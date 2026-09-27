"""Chunk cassation records without losing their citation metadata."""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_cases(cases: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1_400,
        chunk_overlap=220,
        separators=["\n\n", "\n", "።", "፡", " ", ""],
    )
    chunks: list[Document] = []
    for case in cases:
        case_chunks = splitter.split_documents([case])
        for index, chunk in enumerate(case_chunks):
            chunk.metadata["chunk_index"] = index
        chunks.extend(case_chunks)
    return chunks
