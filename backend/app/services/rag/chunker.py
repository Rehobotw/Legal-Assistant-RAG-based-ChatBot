"""Chunk cassation records without losing their citation metadata."""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_cases(cases: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1_200,
        chunk_overlap=250,
        separators=["\n\n", "\n", "።", "፡", " ", ""],
    )
    chunks: list[Document] = []
    for case in cases:
        case_chunks = splitter.split_documents([case])
        case_no = case.metadata.get("case_number", "")
        vol = case.metadata.get("volume", "")
        total_chunks = len(case_chunks)

        for index, chunk in enumerate(case_chunks):
            chunk.metadata["chunk_index"] = index
            chunk.metadata["total_chunks"] = total_chunks
            chunk.metadata["document_id"] = case_no
            if "page" in case.metadata:
                chunk.metadata["page_number"] = case.metadata.get("page")

            header = f"[መዝገብ ቁጥር: {case_no} | Volume: {vol} | Chunk: {index + 1}/{total_chunks}]"
            if not chunk.page_content.startswith("[መዝገብ ቁጥር:"):
                chunk.page_content = f"{header}\n{chunk.page_content}"
        chunks.extend(case_chunks)
    return chunks


