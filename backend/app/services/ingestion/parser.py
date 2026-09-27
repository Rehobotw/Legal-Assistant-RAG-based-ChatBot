"""Turn the cleaned Amharic law report into individual cassation records."""

import re
from pathlib import Path

from langchain_core.documents import Document


CASE_START = re.compile(r"የሰ\s*/\s*መ\s*/\s*ቁ\.?\s*([0-9]+)")
PAGE_MARKER = re.compile(r"--- PAGE\s+(\d+)")
DATE = re.compile(r"((?:መስከረም|ጥቅምት|ሕዳር|ታህሳስ|ጥር|የካቲት|መጋቢት|ሚያዝያ|ግንቦት|ሰኔ|ሐምሌ|ነሐሴ)\s+\d+\s+ቀን\s+\d+\s+ዓ\s*/?ም)")


def parse_case_records(path: Path) -> list[Document]:
    """Extract case boundaries and citation metadata from a cleaned volume.

    A case record, rather than a page, is the retrieval unit before chunking. This
    means every returned chunk retains its case number, date, court, and source.
    """
    text = path.read_text(encoding="utf-8")
    matches = list(CASE_START.finditer(text))
    records: list[Document] = []
    for position, match in enumerate(matches):
        start = match.start()
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if len(body) < 300:
            continue
        page_before = list(PAGE_MARKER.finditer(text, 0, start))
        page = page_before[-1].group(1) if page_before else ""
        date_match = DATE.search(body[:800])
        records.append(
            Document(
                page_content=body,
                metadata={
                    "case_number": match.group(1),
                    "date": date_match.group(1) if date_match else "",
                    "court": "Federal Supreme Court Cassation Division",
                    "court_am": "የፌዴራል ጠቅላይ ፍርድ ቤት ሰበር ችሎት",
                    "volume": path.stem.replace("_Clean", "").replace("_", " "),
                    "page": page,
                    "source": str(path),
                    "source_file": path.name,
                },
            )
        )
    return records
