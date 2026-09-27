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


def retrieve_cases(query: str, limit: int | None = None) -> list[RetrievedCase]:
    """Retrieve chunks using exact case number metadata filter when present, falling back to hybrid similarity search."""
    store = get_ready_vector_store()
    target_k = limit or settings.rag_top_k
    cases: list[RetrievedCase] = []
    seen_case_numbers: set[str] = set()

    # 1. Exact metadata match if a case number is extracted from query
    extracted_num = _extract_case_number(query)
    if extracted_num:
        try:
            exact_docs = store.get(where={"case_number": extracted_num}, include=["documents", "metadatas"])
            if exact_docs and exact_docs.get("documents"):
                docs = exact_docs["documents"]
                metas = exact_docs["metadatas"]
                for doc, meta in zip(docs, metas):
                    c_num = meta.get("case_number", extracted_num)
                    if c_num not in seen_case_numbers:
                        seen_case_numbers.add(c_num)
                        cases.append(RetrievedCase(content=doc, metadata=meta, score=1.0))
        except Exception as e:
            print(f"Exact case filter failed: {e}")

    # 2. Similarity search for remaining slots or full similarity search
    if len(cases) < target_k:
        candidates = store.similarity_search_with_relevance_scores(
            query,
            k=target_k * 4,
        )
        for document, score in candidates:
            c_num = document.metadata.get("case_number")
            if not c_num or c_num in seen_case_numbers:
                continue
            seen_case_numbers.add(c_num)
            cases.append(RetrievedCase(content=document.page_content, metadata=document.metadata, score=float(score)))
            if len(cases) == target_k:
                break

    return cases

