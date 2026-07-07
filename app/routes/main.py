"""
============================================================
  Main Page Routes
  File: app/routes/main.py
============================================================
"""

from flask import Blueprint, render_template, abort
from app.models import Document, Translation
from app import db
from sqlalchemy import func

main_bp = Blueprint("main", __name__)


# ── Supported languages ──────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = [
    {"code": "hi", "name": "Hindi", "native": "हिन्दी", "flag": "🇮🇳"},
    {"code": "mr", "name": "Marathi", "native": "मराठी", "flag": "🇮🇳"},
    {"code": "ta", "name": "Tamil", "native": "தமிழ்", "flag": "🇮🇳"},
    {"code": "te", "name": "Telugu", "native": "తెలుగు", "flag": "🇮🇳"},
    {"code": "bn", "name": "Bengali", "native": "বাংলা", "flag": "🇮🇳"},
    {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી", "flag": "🇮🇳"},
    {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ", "flag": "🇮🇳"},
    {"code": "ml", "name": "Malayalam", "native": "മലയാളം", "flag": "🇮🇳"},
    {"code": "pa", "name": "Punjabi", "native": "ਪੰਜਾਬੀ", "flag": "🇮🇳"},
    {"code": "or", "name": "Odia", "native": "ଓଡ଼ିଆ", "flag": "🇮🇳"},
    {"code": "ur", "name": "Urdu", "native": "اردو", "flag": "🇮🇳"},
    {"code": "fr", "name": "French", "native": "Français", "flag": "🇫🇷"},
    {"code": "de", "name": "German", "native": "Deutsch", "flag": "🇩🇪"},
    {"code": "es", "name": "Spanish", "native": "Español", "flag": "🇪🇸"},
    {"code": "ar", "name": "Arabic", "native": "العربية", "flag": "🇸🇦"},
    {"code": "zh", "name": "Chinese (Simplified)", "native": "中文", "flag": "🇨🇳"},
    {"code": "ja", "name": "Japanese", "native": "日本語", "flag": "🇯🇵"},
]

SUBJECT_DOMAINS = [
    {"key": "mathematics", "label": "Mathematics"},
    {"key": "science", "label": "Science"},
    {"key": "computer_science", "label": "Computer Science"},
    {"key": "economics", "label": "Economics"},
    {"key": "history", "label": "History & Social Studies"},
    {"key": "default", "label": "General / Other"},
]


@main_bp.route("/")
def index():
    total_docs = Document.query.count()
    total_translations = Translation.query.count()
    recent_docs = Document.query.order_by(Document.upload_date.desc()).limit(5).all()

    lang_stats = (
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

    return render_template(
        "dashboard.html",
        total_docs=total_docs,
        total_translations=total_translations,
        recent_docs=recent_docs,
        lang_stats=lang_stats,
        languages=SUPPORTED_LANGUAGES,
    )


@main_bp.route("/translate")
def translate_page():
    return render_template(
        "translate.html",
        languages=SUPPORTED_LANGUAGES,
        subjects=SUBJECT_DOMAINS,
    )


@main_bp.route("/history")
def history_page():
    translations = (
        Translation.query
        .order_by(Translation.created_at.desc())
        .limit(100)
        .all()
    )
    lang_stats = (
        db.session.query(
            Translation.target_language_name,
            func.count(Translation.id).label("count"),
        )
        .filter(Translation.status == "completed")
        .group_by(Translation.target_language_name)
        .order_by(func.count(Translation.id).desc())
        .all()
    )
    return render_template(
        "history.html",
        translations=translations,
        lang_stats=lang_stats,
    )


@main_bp.route("/documents")
def documents_page():
    docs = Document.query.order_by(Document.upload_date.desc()).all()
    return render_template("documents.html", documents=docs)


@main_bp.route("/translation/<int:translation_id>")
def translation_detail(translation_id):
    t = Translation.query.get_or_404(translation_id)
    return render_template("translation_detail.html", translation=t)
