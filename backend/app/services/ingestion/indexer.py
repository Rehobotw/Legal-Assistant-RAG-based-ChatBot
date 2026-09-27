"""Build the persistent Chroma index from the local raw law-report corpus."""

from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.core.config import settings
from app.services.ingestion.loaders.pdf_loader import load_pdf_file
from app.services.ingestion.parser import parse_case_records, parse_case_text
from app.services.rag.chunker import chunk_cases
from app.services.rag.embeddings import get_embeddings


SUPPORTED_SUFFIXES = {".pdf", ".txt"}


def _load_cases(source: Path):
    if source.suffix.lower() == ".txt":
        return parse_case_records(source)

    pages = load_pdf_file(source)
    text = "\n\n".join(
        f"--- PAGE {page.metadata.get('page', index) + 1} ---\n{page.page_content}"
        for index, page in enumerate(pages)
    )
    return parse_case_text(
        text,
        source=str(source),
        source_file=source.name,
        volume=source.stem.replace("_", " "),
    )


def _chunk_ids(chunks) -> list[str]:
    """Stable IDs make an index rebuild reproducible and prevent duplicates."""
    return [
        str(uuid5(NAMESPACE_URL, f"{chunk.metadata['source']}:{chunk.metadata['case_number']}:{chunk.metadata['chunk_index']}"))
        for chunk in chunks
    ]


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

    cases = [case for source in sources for case in _load_cases(source)]
    if not cases:
        raise ValueError("No cassation case records could be parsed from the raw corpus.")
    chunks = chunk_cases(cases)
    store = Chroma(
        collection_name=settings.chroma_collection_name,
        persist_directory=settings.chroma_persist_directory,
        embedding_function=get_embeddings(),
    )
    existing_count = store._collection.count()
    if recreate and existing_count:
        store.delete_collection()
    elif existing_count:
        raise RuntimeError("The precedent index already exists. Run ingestion with --recreate to replace it.")

    Chroma.from_documents(
        chunks,
        embedding=get_embeddings(),
        ids=_chunk_ids(chunks),
        collection_name=settings.chroma_collection_name,
        persist_directory=settings.chroma_persist_directory,
    )
    return len(cases), len(chunks)
