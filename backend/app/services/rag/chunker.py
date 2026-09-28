from __future__ import annotations

import re
from bisect import bisect_right

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 1_200
CHUNK_OVERLAP = 150
HEADER_RESERVE = 80  # characters kept free for the citation header

# Paragraph -> full stop variants -> word -> character.
SEPARATORS = ["\n\n", "፡፡", "።", " ", ""]

_CASE_HEADER_SPLIT = re.compile(r"(?m)^(?=የሰ/መ/ቁ\.?\s*\d+)")
_CASE_NO = re.compile(r"የሰ/መ/ቁ\.?\s*(\d+)")
_PAGE_MARKER = re.compile(r"(?m)^--- PAGE (\d+) \([^)]*\) ---[ \t]*$")
_TRAILING_PAGE_NO = re.compile(r"\n[ \t]*\d{1,4}[ \t]*$")
_SENTENCE_END = ("፡፡", "።")


def _unwrap(body: str) -> str:
    """Join hard-wrapped lines; keep blank lines as paragraph breaks."""
    body = re.sub(r"(?<!\n)\n(?!\n)", " ", body)
    body = re.sub(r"[ \t]+", " ", body)
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def _clean(text: str) -> tuple[str, list[int], list[int]]:
    """Return (clean_text, page_start_offsets, page_numbers).

    Offsets are positions in clean_text where each source page begins. If the
    text has no page markers, both lists are empty.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = _PAGE_MARKER.split(text)  # [pre, page, body, page, body, ...]

    if len(parts) == 1:
        return _unwrap(text), [], []

    out: list[str] = []
    starts: list[int] = []
    pages: list[int] = []
    pos = 0

    pre = _unwrap(parts[0])
    if pre:
        out.append(pre)
        pos = len(pre)

    for page, body in zip(parts[1::2], parts[2::2]):
        body = _TRAILING_PAGE_NO.sub("", body.rstrip())  # printed page number
        body = _unwrap(body)
        if not body:
            continue
        if out:
            # Sentence running across the page break -> plain space.
            sep = "\n\n" if out[-1].endswith(_SENTENCE_END) else " "
            out.append(sep)
            pos += len(sep)
        starts.append(pos)
        pages.append(int(page))
        out.append(body)
        pos += len(body)

    return "".join(out), starts, pages


def _split_by_case(doc: Document) -> list[Document]:
    """Split a Document holding several cases into one Document per case."""
    text = doc.page_content.replace("\r\n", "\n")
    pieces = [p for p in _CASE_HEADER_SPLIT.split(text) if p.strip()]
    headed = [p for p in pieces if _CASE_NO.match(p)]
    if len(headed) <= 1:
        return [doc]

    cases: list[Document] = []
    for piece in pieces:
        m = _CASE_NO.match(piece)
        if not m:
            continue  # front matter before the first case (title page)
        meta = dict(doc.metadata)
        meta["case_number"] = m.group(1)
        cases.append(Document(page_content=piece, metadata=meta))
    return cases


def chunk_cases(
    cases: list[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    add_header: bool = True,
) -> list[Document]:
    reserve = HEADER_RESERVE if add_header else 0
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size - reserve,
        chunk_overlap=chunk_overlap,
        separators=SEPARATORS,
        add_start_index=True,
    )

    chunks: list[Document] = []
    for source in cases:
        for case in _split_by_case(source):
            text, page_starts, page_nums = _clean(case.page_content)
            if not text:
                continue

            if not case.metadata.get("case_number"):
                m = _CASE_NO.search(text[:300])
                if m:
                    case.metadata["case_number"] = m.group(1)

            case_no = str(case.metadata.get("case_number", ""))
            vol = str(case.metadata.get("volume", ""))
            fallback_page = case.metadata.get("page")

            case_chunks = splitter.split_documents(
                [Document(page_content=text, metadata=dict(case.metadata))]
            )
            total = len(case_chunks)

            for index, chunk in enumerate(case_chunks):
                start = chunk.metadata.get("start_index", 0)
                end = start + max(len(chunk.page_content) - 1, 0)

                if page_starts:
                    first = page_nums[max(bisect_right(page_starts, start) - 1, 0)]
                    last = page_nums[max(bisect_right(page_starts, end) - 1, 0)]
                    chunk.metadata["page_number"] = first
                    chunk.metadata["page_end"] = last
                elif fallback_page is not None:
                    chunk.metadata["page_number"] = fallback_page

                chunk.metadata["case_number"] = case_no
                chunk.metadata["document_id"] = case_no
                chunk.metadata["chunk_index"] = index
                chunk.metadata["total_chunks"] = total

                if add_header:
                    header = (
                        f"[መዝገብ ቁጥር: {case_no} | Volume: {vol} | "
                        f"Chunk: {index + 1}/{total}]"
                    )
                    chunk.page_content = f"{header}\n{chunk.page_content}"

            chunks.extend(case_chunks)
    return chunks