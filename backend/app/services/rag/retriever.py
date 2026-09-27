import re
from dataclasses import dataclass

from app.core.config import settings
from app.services.rag.vector_store import get_ready_vector_store


@dataclass(frozen=True)
class RetrievedCase:
    content: str
    metadata: dict
    score: float


def _extract_case_number(query: str) -> str | None:
    """Extract case number digits from Ethiopian query patterns like መዝገብ ቁጥር 130665 or መ/ቁ 130665."""
    patterns = [
        r"(?:መዝገብ\s*ቁጥር|መ/ቁ|መ/ቁጥር|ቁጥር|case\s*no\.?|file\s*no\.?)\s*[:፡]?\s*(\d{4,7})",
        r"\b(\d{5,7})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _retrieve_parent_document_window(
    store, case_number: str, target_chunk_index: int | None = None
) -> tuple[str, dict]:
    """Retrieve parent document chunks for a case_number and sort them chronologically by chunk_index."""
    try:
        case_docs = store.get(where={"case_number": case_number}, include=["documents", "metadatas"])
        if case_docs and case_docs.get("documents"):
            docs = case_docs["documents"]
            metas = case_docs["metadatas"]
            paired = sorted(zip(metas, docs), key=lambda x: x[0].get("chunk_index", 0))

            if target_chunk_index is not None and len(paired) > 6:
                start_idx = max(0, target_chunk_index - 1)
                end_idx = min(len(paired), target_chunk_index + 2)
                paired = paired[start_idx:end_idx]

            full_content = "\n\n".join(doc for _, doc in paired)
            meta = {"case_number": case_number, **paired[0][0]}
            return full_content, meta
    except Exception as e:
        print(f"Parent window retrieval failed for case {case_number}: {e}")
    return "", {}


def retrieve_cases(query: str, limit: int | None = None, score_threshold: float = 0.7) -> list[RetrievedCase]:
    """Retrieve chunks using exact case number metadata filter when present, falling back to similarity search with score thresholding."""
    store = get_ready_vector_store()
    target_k = limit or settings.rag_top_k
    cases: list[RetrievedCase] = []
    seen_case_numbers: set[str] = set()

    # 1. Exact metadata match if a case number is extracted from query
    extracted_num = _extract_case_number(query)
    if extracted_num:
        full_content, meta = _retrieve_parent_document_window(store, extracted_num)
        if full_content:
            seen_case_numbers.add(extracted_num)
            cases.append(RetrievedCase(content=full_content, metadata=meta, score=1.0))

    # 2. Similarity search for remaining slots with similarity score threshold filtering
    if len(cases) < target_k:
        try:
            candidates = store.similarity_search_with_relevance_scores(
                query,
                k=target_k * 3,
                score_threshold=score_threshold,
            )
        except TypeError:
            candidates = store.similarity_search_with_relevance_scores(
                query,
                k=target_k * 3,
            )

        for document, score in candidates:
            score_val = float(score)
            if score_val < score_threshold:
                continue
            c_num = document.metadata.get("case_number")
            if not c_num or c_num in seen_case_numbers:
                continue
            seen_case_numbers.add(c_num)

            target_idx = document.metadata.get("chunk_index")
            full_content, meta = _retrieve_parent_document_window(store, c_num, target_chunk_index=target_idx)
            if not full_content:
                full_content = document.page_content
                meta = document.metadata
            else:
                meta = {**document.metadata, **meta}

            cases.append(RetrievedCase(content=full_content, metadata=meta, score=score_val))
            if len(cases) == target_k:
                break

    return cases




