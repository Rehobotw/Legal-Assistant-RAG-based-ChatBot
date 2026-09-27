"""Build the persistent Chroma index from the local raw law-report corpus."""

from pathlib import Path

from app.core.config import settings
from app.services.ingestion.parser import parse_case_records
from app.services.rag.chunker import chunk_cases
from app.services.rag.embeddings import get_embeddings


SUPPORTED_SUFFIXES = {".txt"}


def build_index(recreate: bool = False) -> tuple[int, int]:
    """Index all cleaned text volumes and return ``(case_count, chunk_count)``.

    Recreating is deliberate: it prevents duplicates after the source corpus or
    parsing rules have changed.
    """
    from langchain_chroma import Chroma

    raw_directory = Path(settings.rag_data_dir)
    sources = sorted(path for path in raw_directory.rglob("*") if path.suffix.lower() in SUPPORTED_SUFFIXES)
    if not sources:
        raise FileNotFoundError(f"No cleaned text volumes found in {raw_directory}.")

    cases = [case for source in sources for case in parse_case_records(source)]
    if not cases:
        raise ValueError("No cassation case records could be parsed from the raw corpus.")
    chunks = chunk_cases(cases)
    store = Chroma(
        collection_name=settings.chroma_collection_name,
        persist_directory=settings.chroma_persist_directory,
        embedding_function=get_embeddings(),
    )
    if recreate:
        store.delete_collection()
        store = Chroma.from_documents(
            chunks,
            embedding=get_embeddings(),
            collection_name=settings.chroma_collection_name,
            persist_directory=settings.chroma_persist_directory,
        )
    else:
        store.add_documents(chunks)
    return len(cases), len(chunks)
