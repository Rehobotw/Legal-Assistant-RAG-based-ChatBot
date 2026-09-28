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


def _clean_boundary_text(text: str) -> str:
    """
    Remove dangling leading/trailing punctuation fragments, orphan characters,
    and trailing line breaks at chunk/sentence boundaries.
    """
    if not text:
        return ""

    # Remove chunk headers if present
    text = re.sub(r"\[መዝገብ ቁጥር:[^\]]+\]", "", text)
    text = re.sub(r"\[Case No\.[^\]]+\]", "", text, flags=re.IGNORECASE).strip()

    # Strip leading orphan punctuation (e.g. ::, 。, ,, ), etc.)
    text = re.sub(r"^\s*[፡።፣፤፥፦፧፨\.\,\:\;\)\s]+", "", text)

    return text.strip()


def _join_chunks_cleanly(chunks: list[str]) -> str:
    """
    Cleanly concatenate adjacent page chunks for a case:
    - Strips chunk headers and leading/trailing boundary noise.
    - Resolves overlapping text between adjacent chunk boundaries.
    - Handles leading ASCII and Amharic boundary punctuation seamlessly.
    """
    cleaned_chunks = []
    for c in chunks:
        cleaned = re.sub(r"\[መዝገብ ቁጥር:[^\]]+\]", "", c)
        cleaned = re.sub(r"\[Case No\.[^\]]+\]", "", cleaned, flags=re.IGNORECASE).strip()
        if cleaned:
            cleaned_chunks.append(cleaned)

    if not cleaned_chunks:
        return ""

    combined = cleaned_chunks[0]

    for next_chunk in cleaned_chunks[1:]:
        max_overlap = min(len(combined), len(next_chunk), 100)
        overlap_found = 0
        for length in range(max_overlap, 10, -1):
            suffix = combined[-length:]
            if next_chunk.startswith(suffix):
                overlap_found = length
                break

        if overlap_found > 0:
            next_chunk = next_chunk[overlap_found:].strip()

        if not next_chunk:
            continue

        combined_trimmed = combined.rstrip()
        next_trimmed = next_chunk.lstrip()

        if re.match(r"^[፡።፣፤፥፦፧፨\.\,\:\;\)]", next_trimmed):
            combined = combined_trimmed + " " + next_trimmed
        else:
            combined = combined_trimmed + "\n\n" + next_chunk

    return combined.strip()



def _retrieve_parent_document_window(
    store, case_number: str
) -> tuple[str, dict, int, int]:
    """
    Retrieve ALL chunks for a case_number, deduplicated and sorted by page_number and chunk_index.
    
    Returns:
        tuple: (full_content, metadata, start_page, end_page)
    """
    try:
        case_docs = None
        case_num_str = str(case_number).strip()

        # Primary lookup by case_number (string)
        try:
            case_docs = store.get(where={"case_number": case_num_str}, include=["documents", "metadatas"])
        except Exception:
            pass

        # Secondary lookup by document_id if case_number yields nothing
        if not case_docs or not case_docs.get("documents"):
            try:
                case_docs = store.get(where={"document_id": case_num_str}, include=["documents", "metadatas"])
            except Exception:
                pass

        # Tertiary lookup if case_number is numeric integer
        if (not case_docs or not case_docs.get("documents")) and case_num_str.isdigit():
            try:
                case_docs = store.get(where={"case_number": int(case_num_str)}, include=["documents", "metadatas"])
            except Exception:
                pass

        if case_docs and case_docs.get("documents"):
            docs = case_docs["documents"]
            metas = case_docs["metadatas"]

            # Deduplicate by chunk_index / content
            seen_indexes = set()
            unique_paired = []
            for meta, doc in zip(metas, docs):
                meta_dict = meta or {}
                idx = meta_dict.get("chunk_index")
                if idx is None or idx in seen_indexes:
                    if (meta_dict, doc) not in unique_paired:
                        unique_paired.append((meta_dict, doc))
                else:
                    seen_indexes.add(idx)
                    unique_paired.append((meta_dict, doc))

            # Sort sequentially: page_number first, then chunk_index
            def _sort_key(item):
                meta_dict = item[0]
                page_val = meta_dict.get("page_number", meta_dict.get("page", 0))
                try:
                    page_int = int(page_val) if page_val is not None and str(page_val).isdigit() else 0
                except (ValueError, TypeError):
                    page_int = 0
                chunk_val = meta_dict.get("chunk_index", 0)
                try:
                    chunk_int = int(chunk_val) if chunk_val is not None and str(chunk_val).isdigit() else 0
                except (ValueError, TypeError):
                    chunk_int = 0
                return (page_int, chunk_int)

            paired = sorted(unique_paired, key=_sort_key)
            
            # Concatenate all sorted chunks cleanly into a continuous text block
            full_content = _join_chunks_cleanly([doc for _, doc in paired])
            
            # Calculate page range
            pages = []
            for meta_dict, _ in paired:
                page_val = meta_dict.get("page_number", meta_dict.get("page", 0))
                try:
                    page_int = int(page_val) if page_val is not None and str(page_val).isdigit() else 0
                    if page_int > 0:
                        pages.append(page_int)
                except (ValueError, TypeError):
                    pass
            
            start_page = min(pages) if pages else 0
            end_page = max(pages) if pages else 0
            
            # Merge metadata from first chunk with page range info
            meta = {
                "case_number": case_num_str, 
                **(paired[0][0] if paired else {}),
                "start_page": start_page,
                "end_page": end_page,
            }
            
            return full_content, meta, start_page, end_page
    except Exception as e:
        print(f"Parent document retrieval failed for case {case_number}: {e}")
    return "", {}, 0, 0


def _aggregate_candidate_chunks(candidate_pairs: list) -> tuple[str, dict, int, int]:
    """Fallback: aggregate and sort candidate document chunks from similarity search when store.get is unavailable."""
    if not candidate_pairs:
        return "", {}, 0, 0

    unique_paired = []
    seen_indexes = set()
    for doc, _score in candidate_pairs:
        meta = doc.metadata or {}
        idx = meta.get("chunk_index")
        if idx is None or idx in seen_indexes:
            if (meta, doc.page_content) not in unique_paired:
                unique_paired.append((meta, doc.page_content))
        else:
            seen_indexes.add(idx)
            unique_paired.append((meta, doc.page_content))

    def _sort_key(item):
        meta_dict = item[0]
        page_val = meta_dict.get("page_number", meta_dict.get("page", 0))
        try:
            page_int = int(page_val) if page_val is not None and str(page_val).isdigit() else 0
        except (ValueError, TypeError):
            page_int = 0
        chunk_val = meta_dict.get("chunk_index", 0)
        try:
            chunk_int = int(chunk_val) if chunk_val is not None and str(chunk_val).isdigit() else 0
        except (ValueError, TypeError):
            chunk_int = 0
        return (page_int, chunk_int)

    paired = sorted(unique_paired, key=_sort_key)
    full_content = _join_chunks_cleanly([text for _, text in paired])


    pages = []
    for meta_dict, _ in paired:
        page_val = meta_dict.get("page_number", meta_dict.get("page", 0))
        try:
            page_int = int(page_val) if page_val is not None and str(page_val).isdigit() else 0
            if page_int > 0:
                pages.append(page_int)
        except (ValueError, TypeError):
            pass

    start_page = min(pages) if pages else 0
    end_page = max(pages) if pages else 0
    meta = {
        **(paired[0][0] if paired else {}),
        "start_page": start_page,
        "end_page": end_page,
    }
    return full_content, meta, start_page, end_page


def retrieve_cases(query: str, limit: int | None = None, score_threshold: float = 0.65) -> list[RetrievedCase]:
    """
    Hybrid Search combining exact metadata filter matching and dense vector similarity search.
    
    When a case number is detected in the query or retrieved candidates, fetches ALL chunks
    for that case file across all pages, sorted chronologically by page and chunk index to
    maintain the legal narrative structure.
    
    IMPORTANT: When querying a specific case number, ONLY returns content from that case.
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
        # When a specific case number is mentioned, ONLY retrieve that case
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
        # Return immediately - do not search for other cases
        return cases

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

    # 2. Vector Similarity Search (Dense retrieval for top-k capacity)
    # Only run semantic search if no specific case number was extracted
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
            
            # Fallback if store.get returned empty: gather all candidate chunks matching c_num
            if not full_content:
                matched_pairs = [
                    (cand_doc, cand_score) for cand_doc, cand_score in candidates
                    if cand_doc.metadata.get("case_number") == c_num or cand_doc.metadata.get("document_id") == c_num
                ]
                if matched_pairs:
                    full_content, meta, start_page, end_page = _aggregate_candidate_chunks(matched_pairs)

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








