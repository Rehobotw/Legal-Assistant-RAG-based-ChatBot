"""Chunk cassation records without losing their citation metadata."""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_cases(cases: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1_000,
        chunk_overlap=200,
        separators=["\n\n", "\n", "።", "፡", " ", ""],
    )
    chunks: list[Document] = []
    for case in cases:
        case_chunks = splitter.split_documents([case])
        case_no = case.metadata.get("case_number", "")
        vol = case.metadata.get("volume", "")
        header = f"[መዝገብ ቁጥር: {case_no} | Volume: {vol}]"
        for index, chunk in enumerate(case_chunks):
            chunk.metadata["chunk_index"] = index
            if not chunk.page_content.startswith("[መዝገብ ቁጥር:"):
                chunk.page_content = f"{header}\n{chunk.page_content}"
        chunks.extend(case_chunks)
    return chunks

