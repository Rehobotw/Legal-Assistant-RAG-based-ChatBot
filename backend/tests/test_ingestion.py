from pathlib import Path

from app.services.ingestion.parser import parse_case_records
from app.services.rag.chunker import chunk_cases


RAW_VOLUME = Path(__file__).parents[1] / "data/raw/Volume_21_Clean.txt"


def test_raw_volume_is_parsed_into_citable_case_records() -> None:
    cases = parse_case_records(RAW_VOLUME)

    assert len(cases) == 70
    assert cases[0].metadata["case_number"] == "130665"
    assert cases[0].metadata["date"] == "ሕዳር 13 ቀን 2009 ዓ/ም"
    assert cases[0].metadata["page"] == "2"


def test_case_chunks_keep_their_citation_metadata() -> None:
    chunks = chunk_cases(parse_case_records(RAW_VOLUME)[:1])

    assert len(chunks) > 1
    assert {chunk.metadata["case_number"] for chunk in chunks} == {"130665"}
    assert [chunk.metadata["chunk_index"] for chunk in chunks] == list(range(len(chunks)))
