"""
============================================================
  Database Models
  File: app/models.py
============================================================
"""

from datetime import datetime, timezone
from app import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)   # pdf / presentation / document / text
    file_size = db.Column(db.Integer, default=0)           # bytes
    page_count = db.Column(db.Integer, default=0)
    word_count = db.Column(db.Integer, default=0)
    subject_domain = db.Column(db.String(50), default="default")
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default="uploaded")  # uploaded / indexed / error

    translations = db.relationship("Translation", backref="document", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "word_count": self.word_count,
            "subject_domain": self.subject_domain,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "status": self.status,
            "translation_count": len(self.translations),
        }


class Translation(db.Model):
    __tablename__ = "translations"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    target_language_code = db.Column(db.String(10), nullable=False)
    target_language_name = db.Column(db.String(50), nullable=False)
    subject_domain = db.Column(db.String(50), default="default")
    model_used = db.Column(db.String(100))
    source_word_count = db.Column(db.Integer, default=0)
    translated_word_count = db.Column(db.Integer, default=0)
    translated_text = db.Column(db.Text)
    rag_context_used = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="pending")   # pending / completed / error
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Float, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "document_name": self.document.original_filename if self.document else "",
            "target_language_code": self.target_language_code,
            "target_language_name": self.target_language_name,
            "subject_domain": self.subject_domain,
            "model_used": self.model_used,
            "source_word_count": self.source_word_count,
            "translated_word_count": self.translated_word_count,
            "rag_context_used": self.rag_context_used,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }
