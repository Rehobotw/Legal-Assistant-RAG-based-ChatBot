import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest
from app.services.rag.retriever import RetrievedCase
import app.services.rag.pipeline as pipeline


def test_chat_returns_ranked_case_citation(monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "_holding", lambda case, amharic: "የተረጋገጠ የውሳኔ ማጠቃለያ")
    monkeypatch.setattr(
        pipeline,
        "retrieve_cases",
        lambda _: [
            RetrievedCase(
                content="ውሳኔ ሠራተኛው የማስጠንቀቂያ ጊዜ ካልሰጠ የሕግ ውጤት ይኖራል።",
                metadata={
                    "case_number": "130665",
                    "date": "ሕዳር 13 ቀን 2009 ዓ/ም",
                    "court": "Federal Supreme Court Cassation Division",
                    "volume": "Volume 21",
                    "page": "2",
                },
                score=0.92,
            )
        ],
    )
    response = pipeline.answer_query("termination notice")

    assert response.query == "termination notice"
    assert response.answer
    assert response.citations[0].file_number == "130665"
    assert response.citations[0].rank == 1
    assert response.citations[0].holding


def test_chat_rejects_blank_query() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message=" ")


def test_chat_accepts_short_case_lookup() -> None:
    assert ChatRequest(message="1").message == "1"
