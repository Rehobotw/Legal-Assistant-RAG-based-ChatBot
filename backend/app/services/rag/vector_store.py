"""Persistent local Chroma collection for cassation decisions."""

from pathlib import Path

from app.core.config import settings
from app.services.rag.embeddings import get_embeddings

_vector_store_instance = None


class IndexNotReadyError(RuntimeError):
    """Raised when retrieval is attempted before the local corpus is indexed."""


def get_vector_store():
    global _vector_store_instance
    if _vector_store_instance is None:
        from langchain_chroma import Chroma

        _vector_store_instance = Chroma(
            collection_name=settings.chroma_collection_name,
            persist_directory=str(Path(settings.chroma_persist_directory)),
            embedding_function=get_embeddings(),
        )
    return _vector_store_instance


def get_ready_vector_store():
    store = get_vector_store()
    if store._collection.count() == 0:
        raise IndexNotReadyError(
            "The precedent index is empty. Run `python scripts/ingest.py --recreate` from backend/."
        )
    return store
