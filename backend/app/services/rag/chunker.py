"""Chunk cassation records without losing their citation metadata."""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_cases(cases: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1_400,
        chunk_overlap=220,
        separators=["\n\n", "\n", "።", "፡", " ", ""],
    )
    chunks = splitter.split_documents(cases)
    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = index
    return chunks
