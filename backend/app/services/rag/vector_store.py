"""Persistent local Chroma collection for cassation decisions."""

from pathlib import Path

from app.core.config import settings
from app.services.rag.embeddings import get_embeddings


def get_vector_store():
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=settings.chroma_collection_name,
        persist_directory=str(Path(settings.chroma_persist_directory)),
        embedding_function=get_embeddings(),
    )
