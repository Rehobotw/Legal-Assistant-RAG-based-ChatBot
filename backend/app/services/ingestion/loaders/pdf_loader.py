"""PDF law-report loader."""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


def load_pdf_file(path: Path) -> list[Document]:
    """Load every PDF page and retain the source filename in metadata."""
    documents: list[Document] = PyPDFLoader(str(path)).load()
    for document in documents:
        document.metadata["source_file"] = path.name
    return documents
