import re
from dataclasses import dataclass

from app.core.config import settings
from app.services.rag.vector_store import get_ready_vector_store


@dataclass(frozen=True)
class RetrievedCase:
    content: str
    metadata: dict
    score: float
    match_type: str = "semantic"  # "exact_match" or "semantic"


def extract_query_metadata(query: str) -> dict[str, str]:
    """
    Extract case_number and volume from query string using comprehensive regex patterns.
    
    Supports formats:
    - መዝገብ ቁጥር 130665, መ/ቁ 130665, Case No. 130665
    - ቅጽ 21, Volume 21, Vol. 21
    - Bare numbers like 130665
    """
    extracted = {}

    # Case Number Extraction - Enhanced patterns
    case_patterns = [
        r"(?:መዝገብ\s*ቁጥር|መ/ቁ|መ/ቁጥር|ቁጥር|case\s*no\.?|file\s*no\.?|case\s*number)\s*[:፡]?\s*(\d{4,7})",
        r"(?:መ|ሐ|case)\s*/?\s*ቁ\.?\s*(\d{4,7})",  # Handles መ/ቁ. or case/ቁ
        r"\b(\d{5,7})\b",  # Bare 5-7 digit numbers
    ]
    for pattern in case_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            extracted["case_number"] = match.group(1)
            break

    # Volume Extraction - Enhanced patterns
    vol_patterns = [
        r"(?:ቅጽ|ቅፅ|volume|vol\.?)\s*[:፡]?\s*(\d{1,3})",
        r"(?:ቅጽ|ቅፅ)\s*(?:ቁጥር)?\s*[:፡]?\s*(\d{1,3})",  # Handles "ቅጽ ቁጥር 21"
    ]
    for pattern in vol_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            extracted["volume"] = match.group(1)
            break

    return extracted


def _extract_case_number(query: str) -> str | None:
    """Extract case number digits for backward compatibility."""
    meta = extract_query_metadata(query)
    return meta.get("case_number")


def _retrieve_parent_document_window(
    store, case_number: str
) -> tuple[str, dict, int, int]:
    """
    Retrieve ALL chunks for a case_number, deduplicated and sorted by page_number and chunk_index.
    
    Returns:
        tuple: (full_content, metadata, start_page, end_page)
    """
    try:
        case_docs = store.get(where={"case_number": case_number}, include=["documents", "metadatas"])
        if case_docs and case_docs.get("documents"):
            docs = case_docs["documents"]
            metas = case_docs["metadatas"]

            # Deduplicate by chunk_index
            seen_indexes = set()
            unique_paired = []
            for meta, doc in zip(metas, docs):
                idx = meta.get("chunk_index", 0)
                if idx not in seen_indexes:
                    seen_indexes.add(idx)
                    unique_paired.append((meta, doc))

            # Sort by page_number first, then chunk_index
            def _sort_key(item):
                meta_dict = item[0]
                page_val = meta_dict.get("page_number", meta_dict.get("page", 0))
                page_int = int(page_val) if str(page_val).isdigit() else 0
                chunk_int = int(meta_dict.get("chunk_index", 0))
                return (page_int, chunk_int)

            paired = sorted(unique_paired, key=_sort_key)
            
            # Concatenate all chunks in order
            full_content = "\n\n".join(doc for _, doc in paired)
            
            # Calculate page range
            pages = []
            for meta_dict, _ in paired:
                page_val = meta_dict.get("page_number", meta_dict.get("page", 0))
                page_int = int(page_val) if str(page_val).isdigit() else 0
                if page_int > 0:
                    pages.append(page_int)
            
            start_page = min(pages) if pages else 0
            end_page = max(pages) if pages else 0
            
            # Merge metadata from first chunk with page range info
            meta = {
                "case_number": case_number, 
                **paired[0][0],
                "start_page": start_page,
                "end_page": end_page,
            }
            
            return full_content, meta, start_page, end_page
    except Exception as e:
        print(f"Parent document retrieval failed for case {case_number}: {e}")
    return "", {}, 0, 0


def retrieve_cases(query: str, limit: int | None = None, score_threshold: float = 0.65) -> list[RetrievedCase]:
    """
    Hybrid Search combining exact metadata filter matching and dense vector similarity search.
    
    When a case number is detected in the query, fetches ALL chunks for that case file
    across all pages, sorted chronologically to maintain the legal narrative structure.
    """
    store = get_ready_vector_store()
    target_k = limit or settings.rag_top_k
    cases: list[RetrievedCase] = []
    seen_case_numbers: set[str] = set()

    meta_extracted = extract_query_metadata(query)
    extracted_case_num = meta_extracted.get("case_number")
    extracted_volume = meta_extracted.get("volume")

    # 1. Exact Metadata Filter Lookup (Highest precedence)
    if extracted_case_num:
        full_content, meta, start_page, end_page = _retrieve_parent_document_window(store, extracted_case_num)
        if full_content:
            seen_case_numbers.add(extracted_case_num)
            cases.append(
                RetrievedCase(
                    content=full_content,
                    metadata={
                        **meta,
                        "start_page": start_page,
                        "end_page": end_page,
                    },
                    score=1.0,
                    match_type="exact_match",
                )
            )

    elif extracted_volume:
        try:
            # Query documents matching volume
            vol_target = f"Volume {extracted_volume}"
            vol_docs = store.get(where={"volume": vol_target}, include=["documents", "metadatas"])
            if not vol_docs or not vol_docs.get("documents"):
                vol_docs = store.get(where={"volume": extracted_volume}, include=["documents", "metadatas"])
            if vol_docs and vol_docs.get("metadatas"):
                for meta in vol_docs["metadatas"]:
                    c_num = meta.get("case_number")
                    if c_num and c_num not in seen_case_numbers:
                        full_content, full_meta, start_page, end_page = _retrieve_parent_document_window(store, c_num)
                        if full_content:
                            seen_case_numbers.add(c_num)
                            cases.append(
                                RetrievedCase(
                                    content=full_content,
                                    metadata={
                                        **full_meta,
                                        "start_page": start_page,
                                        "end_page": end_page,
                                    },
                                    score=0.95,
                                    match_type="exact_match",
                                )
                            )
                            if len(cases) >= target_k:
                                break
        except Exception as e:
            print(f"Volume metadata lookup failed: {e}")

    # 2. Vector Similarity Search (Dense retrieval for remaining capacity)
    if len(cases) < target_k:
        try:
            candidates = store.similarity_search_with_relevance_scores(
                query,
                k=target_k * 4,
                score_threshold=score_threshold,
            )
        except TypeError:
            candidates = store.similarity_search_with_relevance_scores(
                query,
                k=target_k * 4,
            )

        for document, score in candidates:
            score_val = float(score)
            if score_val < score_threshold:
                continue
            c_num = document.metadata.get("case_number") or document.metadata.get("document_id")
            if not c_num or c_num in seen_case_numbers:
                continue
            seen_case_numbers.add(c_num)

            full_content, meta, start_page, end_page = _retrieve_parent_document_window(store, c_num)
            if not full_content:
                full_content = document.page_content
                meta = document.metadata
                start_page = int(meta.get("page_number", meta.get("page", 0)))
                end_page = start_page
            else:
                meta = {
                    **document.metadata, 
                    **meta,
                    "start_page": start_page,
                    "end_page": end_page,
                }

            cases.append(
                RetrievedCase(
                    content=full_content,
                    metadata=meta,
                    score=score_val,
                    match_type="semantic",
                )
            )
            if len(cases) == target_k:
                break

    return cases







