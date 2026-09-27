"""Citation-preserving retrieval over the Federal Supreme Court corpus."""

from dataclasses import dataclass

from app.core.config import settings
from app.services.rag.vector_store import get_vector_store


@dataclass(frozen=True)
class RetrievedCase:
    content: str
    metadata: dict
    score: float


def retrieve_cases(query: str, limit: int | None = None) -> list[RetrievedCase]:
    """Retrieve chunks, deduplicate by case number, and return rank-ordered cases."""
    store = get_vector_store()
    candidates = store.similarity_search_with_relevance_scores(
        query,
        k=(limit or settings.rag_top_k) * 3,
    )
    cases: list[RetrievedCase] = []
    seen_case_numbers: set[str] = set()
    for document, score in candidates:
        case_number = document.metadata.get("case_number")
        if not case_number or case_number in seen_case_numbers:
            continue
        seen_case_numbers.add(case_number)
        cases.append(RetrievedCase(document.page_content, document.metadata, float(score)))
        if len(cases) == (limit or settings.rag_top_k):
            break
    return cases
