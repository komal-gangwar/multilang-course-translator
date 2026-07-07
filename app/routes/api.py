"""
============================================================
  REST API Routes
  File: app/routes/api.py
============================================================
"""

import os
import time
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app import db
from app.models import Document, Translation
from app.utils.document_processor import (
    extract_text,
    chunk_text,
    word_count,
    allowed_file,
    preview,
)
from app.utils.watsonx_client import translate_text, test_connection
from app.rag.vector_store import get_vector_store, index_document_chunks
from app.agent_instructions import build_system_prompt, build_translation_prompt

api_bp = Blueprint("api", __name__)
logger = logging.getLogger(__name__)


# ── Helper ───────────────────────────────────────────────────────────────────

def _error(msg: str, code: int = 400):
    return jsonify({"success": False, "error": msg}), code


def _ok(data: dict):
    return jsonify({"success": True, **data})


# ── Upload ────────────────────────────────────────────────────────────────────

@api_bp.route("/upload", methods=["POST"])
def upload_document():
    """Upload and index a document for translation."""
    if "file" not in request.files:
        return _error("No file part in request.")

    file = request.files["file"]
    if file.filename == "":
        return _error("No file selected.")

    if not allowed_file(file.filename):
        return _error("Unsupported file type. Allowed: PDF, PPTX, DOCX, TXT, MD")

    subject_domain = request.form.get("subject_domain", "default")

    filename_safe = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename_safe}"
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    save_path = os.path.join(upload_dir, unique_name)

    file_bytes = file.read()
    file_size = len(file_bytes)

    # Extract text
    text, page_count, file_type = extract_text(file_bytes, file.filename)
    wc = word_count(text)

    if not text.strip():
        return _error("Could not extract text from the file. It may be image-only or encrypted.")

    # Save to disk
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    # Save to DB
    doc = Document(
        filename=unique_name,
        original_filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        page_count=page_count,
        word_count=wc,
        subject_domain=subject_domain,
        status="indexed",
    )
    db.session.add(doc)
    db.session.commit()

    # Index into vector store (background-style — runs synchronously but fast for small docs)
    try:
        chunks = chunk_text(text, chunk_size=400, overlap=40)
        index_document_chunks(str(doc.id), chunks, subject=subject_domain)
    except Exception as e:
        logger.warning(f"RAG indexing skipped for doc {doc.id}: {e}")

    return _ok({
        "document": doc.to_dict(),
        "preview": preview(text, 300),
        "message": f"Uploaded and indexed '{file.filename}' successfully.",
    })


# ── Translate ─────────────────────────────────────────────────────────────────

@api_bp.route("/translate", methods=["POST"])
def translate_document():
    """Translate an uploaded document using Watsonx Granite + RAG."""
    data = request.get_json(silent=True) or {}

    document_id = data.get("document_id")
    target_lang_code = data.get("target_language_code", "").strip()
    target_lang_name = data.get("target_language_name", "").strip()
    subject_domain = data.get("subject_domain", "default")

    # Validation
    if not document_id:
        return _error("document_id is required.")
    if not target_lang_code or not target_lang_name:
        return _error("target_language_code and target_language_name are required.")

    doc = Document.query.get(document_id)
    if not doc:
        return _error("Document not found.", 404)

    # Load source text
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    file_path = os.path.join(upload_dir, doc.filename)
    if not os.path.exists(file_path):
        return _error("Source file not found on disk.", 404)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    source_text, _, _ = extract_text(file_bytes, doc.original_filename)
    if not source_text.strip():
        return _error("Source text could not be extracted.")

    # RAG context retrieval
    rag_context = ""
    rag_used = False
    try:
        vs = get_vector_store()
        # Use first ~300 chars as a representative query
        query = source_text[:300]
        rag_context = vs.build_context_string(query, k=5, score_threshold=0.25)
        rag_used = bool(rag_context.strip())
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")

    # Build prompts
    system_prompt = build_system_prompt(
        target_language_code=target_lang_code,
        subject_domain=subject_domain,
    )
    user_prompt = build_translation_prompt(
        source_text=source_text,
        target_language_name=target_lang_name,
        rag_context=rag_context,
    )

    # Create DB record
    translation = Translation(
        document_id=doc.id,
        target_language_code=target_lang_code,
        target_language_name=target_lang_name,
        subject_domain=subject_domain,
        model_used=os.getenv("TRANSLATION_MODEL", "ibm/granite-3-3-8b-instruct"),
        source_word_count=word_count(source_text),
        rag_context_used=rag_used,
        status="pending",
    )
    db.session.add(translation)
    db.session.commit()

    # Translate
    start_time = time.time()
    try:
        translated_text = translate_text(
            source_text=source_text,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        duration = time.time() - start_time

        translation.translated_text = translated_text
        translation.translated_word_count = word_count(translated_text)
        translation.status = "completed"
        translation.completed_at = datetime.now(timezone.utc)
        translation.duration_seconds = round(duration, 2)
        db.session.commit()

        return _ok({
            "translation": translation.to_dict(),
            "translated_text": translated_text,
            "rag_context_used": rag_used,
            "duration_seconds": round(duration, 2),
        })

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        translation.status = "error"
        translation.error_message = error_msg
        translation.duration_seconds = round(duration, 2)
        db.session.commit()
        logger.error(f"Translation failed for doc {doc.id}: {e}", exc_info=True)
        return _error(f"Translation failed: {error_msg}", 500)


# ── Documents API ─────────────────────────────────────────────────────────────

@api_bp.route("/documents", methods=["GET"])
def list_documents():
    docs = Document.query.order_by(Document.upload_date.desc()).all()
    return _ok({"documents": [d.to_dict() for d in docs]})


@api_bp.route("/documents/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    file_path = os.path.join(upload_dir, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(doc)
    db.session.commit()
    return _ok({"message": f"Document '{doc.original_filename}' deleted."})


# ── Translations API ──────────────────────────────────────────────────────────

@api_bp.route("/translations", methods=["GET"])
def list_translations():
    limit = request.args.get("limit", 50, type=int)
    translations = (
        Translation.query.order_by(Translation.created_at.desc()).limit(limit).all()
    )
    return _ok({"translations": [t.to_dict() for t in translations]})


@api_bp.route("/translations/<int:t_id>", methods=["GET"])
def get_translation(t_id):
    t = Translation.query.get_or_404(t_id)
    return _ok({"translation": t.to_dict(), "translated_text": t.translated_text})


@api_bp.route("/translations/<int:t_id>", methods=["DELETE"])
def delete_translation(t_id):
    t = Translation.query.get_or_404(t_id)
    db.session.delete(t)
    db.session.commit()
    return _ok({"message": "Translation deleted."})


# ── Stats API ─────────────────────────────────────────────────────────────────

@api_bp.route("/stats", methods=["GET"])
def stats():
    from sqlalchemy import func
    total_docs = Document.query.count()
    total_translations = Translation.query.count()
    completed = Translation.query.filter_by(status="completed").count()
    failed = Translation.query.filter_by(status="error").count()

    lang_usage = (
        db.session.query(
            Translation.target_language_name,
            Translation.target_language_code,
            func.count(Translation.id).label("count"),
        )
        .filter(Translation.status == "completed")
        .group_by(Translation.target_language_name, Translation.target_language_code)
        .order_by(func.count(Translation.id).desc())
        .all()
    )

    domain_usage = (
        db.session.query(
            Translation.subject_domain,
            func.count(Translation.id).label("count"),
        )
        .filter(Translation.status == "completed")
        .group_by(Translation.subject_domain)
        .order_by(func.count(Translation.id).desc())
        .all()
    )

    return _ok({
        "total_documents": total_docs,
        "total_translations": total_translations,
        "completed_translations": completed,
        "failed_translations": failed,
        "language_usage": [
            {"code": r.target_language_code, "name": r.target_language_name, "count": r.count}
            for r in lang_usage
        ],
        "domain_usage": [
            {"domain": r.subject_domain, "count": r.count}
            for r in domain_usage
        ],
    })


# ── Connection test ───────────────────────────────────────────────────────────

@api_bp.route("/test-connection", methods=["GET"])
def test_watsonx():
    result = test_connection()
    return jsonify(result)
