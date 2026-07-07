"""
============================================================
  RAG Pipeline — Vector Store & Retrieval
  File: app/rag/vector_store.py
============================================================
"""

import os
import json
import logging
import pickle
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Lazy imports (heavy deps) — loaded only when needed
_embedder = None
_faiss = None


# The canonical free multilingual embedding model — no HuggingFace auth required.
# If EMBEDDING_MODEL is set in .env, it overrides this default.
_DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# IBM Granite embedding models require HuggingFace authentication (gated repos).
# Reject them and fall back to the safe default so RAG doesn't break on startup.
_GATED_MODEL_PREFIXES = ("ibm/granite-embedding", "ibm/granite-3-embedding")


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("EMBEDDING_MODEL", _DEFAULT_EMBEDDING_MODEL)

        # Guard: reject gated IBM models that need HF auth
        if any(model_name.lower().startswith(p) for p in _GATED_MODEL_PREFIXES):
            logger.warning(
                f"EMBEDDING_MODEL='{model_name}' is a gated HuggingFace repo that "
                f"requires authentication and is not publicly available. "
                f"Falling back to '{_DEFAULT_EMBEDDING_MODEL}'. "
                f"Update EMBEDDING_MODEL in your .env file to fix this permanently."
            )
            model_name = _DEFAULT_EMBEDDING_MODEL

        logger.info(f"Loading embedding model: {model_name}")
        _embedder = SentenceTransformer(model_name)
    return _embedder


def _get_faiss():
    global _faiss
    if _faiss is None:
        import faiss as _f
        _faiss = _f
    return _faiss


class VectorStore:
    """
    Lightweight FAISS-backed vector store for RAG retrieval.

    Stores chunks of academic text (glossaries, curricula, uploaded docs)
    and retrieves semantically similar passages given a query.
    """

    def __init__(self, store_path: str = "app/data/vector_store"):
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.store_path / "faiss.index"
        self.meta_file = self.store_path / "metadata.pkl"

        self.index = None          # FAISS index
        self.metadata: List[dict] = []  # parallel list of metadata per vector

    # ──────────────────────────────────────────────────────────────────────────
    #  Persistence
    # ──────────────────────────────────────────────────────────────────────────

    def save(self):
        """Persist index and metadata to disk."""
        faiss = _get_faiss()
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_file))
            with open(self.meta_file, "wb") as f:
                pickle.dump(self.metadata, f)
            logger.info(f"Vector store saved: {len(self.metadata)} chunks")

    def load(self) -> bool:
        """Load index and metadata from disk. Returns True if successful."""
        faiss = _get_faiss()
        if self.index_file.exists() and self.meta_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                with open(self.meta_file, "rb") as f:
                    self.metadata = pickle.load(f)
                logger.info(f"Vector store loaded: {len(self.metadata)} chunks")
                return True
            except Exception as e:
                logger.warning(f"Failed to load vector store: {e}")
        return False

    # ──────────────────────────────────────────────────────────────────────────
    #  Indexing
    # ──────────────────────────────────────────────────────────────────────────

    def add_texts(self, texts: List[str], metadatas: List[dict]):
        """
        Embed and add a list of text chunks to the index.

        Args:
            texts: List of text strings to index
            metadatas: Corresponding metadata dicts (source, subject, etc.)
        """
        if not texts:
            return

        embedder = _get_embedder()
        faiss = _get_faiss()

        embeddings = embedder.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        embeddings = np.array(embeddings, dtype=np.float32)

        dim = embeddings.shape[1]
        if self.index is None:
            self.index = faiss.IndexFlatIP(dim)  # Inner-product (cosine with normalized vecs)

        self.index.add(embeddings)
        self.metadata.extend(metadatas)
        logger.info(f"Added {len(texts)} chunks to vector store (total: {len(self.metadata)})")

    # ──────────────────────────────────────────────────────────────────────────
    #  Retrieval
    # ──────────────────────────────────────────────────────────────────────────

    def search(self, query: str, k: int = 5) -> List[Tuple[str, dict, float]]:
        """
        Retrieve top-k most similar chunks for a query.

        Returns:
            List of (text, metadata, score) tuples
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        embedder = _get_embedder()
        faiss = _get_faiss()

        query_vec = embedder.encode([query], normalize_embeddings=True)
        query_vec = np.array(query_vec, dtype=np.float32)

        actual_k = min(k, self.index.ntotal)
        scores, indices = self.index.search(query_vec, actual_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.metadata):
                meta = self.metadata[idx]
                results.append((meta.get("text", ""), meta, float(score)))

        return results

    def build_context_string(self, query: str, k: int = 5, score_threshold: float = 0.3) -> str:
        """
        Build a formatted RAG context block ready to inject into a prompt.

        Args:
            query: The source text or a representative sentence from it
            k: Max number of chunks to retrieve
            score_threshold: Minimum cosine similarity to include

        Returns:
            Formatted context string
        """
        results = self.search(query, k=k)
        relevant = [(t, m, s) for t, m, s in results if s >= score_threshold]

        if not relevant:
            return ""

        parts = []
        seen = set()
        for text, meta, score in relevant:
            if text in seen:
                continue
            seen.add(text)
            source = meta.get("source", "reference")
            parts.append(f"[Source: {source}]\n{text}")

        return "\n\n".join(parts)


# ── Singleton instance ──────────────────────────────────────────────────────
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Return the app-wide vector store singleton, loading from disk if available."""
    global _vector_store
    if _vector_store is None:
        store_path = os.getenv("VECTOR_STORE_PATH", "app/data/vector_store")
        _vector_store = VectorStore(store_path=store_path)
        _vector_store.load()
    return _vector_store


def initialize_knowledge_base(glossary_path: str = "app/data/glossaries/academic_glossary.json"):
    """
    Bootstrap the vector store from the bundled academic glossary JSON.
    Call this once at startup or when the glossary changes.
    """
    vs = get_vector_store()

    if vs.index is not None and vs.index.ntotal > 0:
        logger.info("Knowledge base already initialized — skipping.")
        return

    logger.info("Initializing knowledge base from glossary JSON...")
    texts, metas = [], []

    try:
        with open(glossary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning(f"Glossary file not found: {glossary_path}")
        return

    # --- Index subject glossaries ---
    for subject, terms in data.items():
        if subject in ("metadata", "curriculum_frameworks"):
            continue
        for term, translations in terms.items():
            trans_parts = [f"{code}: {val}" for code, val in translations.items()]
            chunk = (
                f"Subject: {subject}\n"
                f"Term: {term}\n"
                f"Translations — {', '.join(trans_parts)}"
            )
            texts.append(chunk)
            metas.append({
                "text": chunk,
                "source": f"Academic Glossary / {subject}",
                "subject": subject,
                "term": term,
            })

    # --- Index curriculum frameworks ---
    for fw in data.get("curriculum_frameworks", []):
        chunk = f"{fw['title']}\n\n{fw['content']}"
        texts.append(chunk)
        metas.append({
            "text": chunk,
            "source": fw["title"],
            "subject": "curriculum",
        })

    vs.add_texts(texts, metas)
    vs.save()
    logger.info(f"Knowledge base initialized with {len(texts)} entries.")


def index_document_chunks(doc_id: str, chunks: List[str], subject: str = "general"):
    """
    Index extracted text chunks from an uploaded document into the vector store.

    Args:
        doc_id: Unique identifier for the document (used as source metadata)
        chunks: List of text chunks extracted from the document
        subject: Subject domain for the document
    """
    vs = get_vector_store()
    metas = [
        {
            "text": chunk,
            "source": f"document/{doc_id}",
            "subject": subject,
            "doc_id": doc_id,
        }
        for chunk in chunks
    ]
    vs.add_texts(chunks, metas)
    vs.save()
