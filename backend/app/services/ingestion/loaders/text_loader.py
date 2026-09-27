"""Load UTF-8 text law reports with LangChain's document abstraction."""

from pathlib import Path

from langchain_core.documents import Document


def load_text_file(path: Path) -> list[Document]:
    """Return a single source document; case parsing happens before chunking."""
    return [
        Document(
            page_content=path.read_text(encoding="utf-8"),
            metadata={"source": str(path), "source_file": path.name},
        )
    ]
