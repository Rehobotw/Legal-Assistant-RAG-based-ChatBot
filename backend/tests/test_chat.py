import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest
from app.services.rag.retriever import RetrievedCase
import app.services.rag.pipeline as pipeline


def test_chat_returns_ranked_case_citation(monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "get_llm_model", lambda: None)
    monkeypatch.setattr(pipeline, "_holding", lambda case, amharic, model=None: "የተረጋገጠ የውሳኔ ማጠቃለያ")
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


def test_chat_handles_quota_exceeded_error(monkeypatch) -> None:
    def _raise_quota(_):
        raise Exception("insufficient_quota 429 credit_balance_exhausted")
    monkeypatch.setattr(pipeline, "retrieve_cases", _raise_quota)

    resp = pipeline.answer_query("termination notice")
    assert "out of API credits" in resp.answer
    assert resp.citations == []


def test_chat_rejects_blank_query() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message=" ")


def test_chat_accepts_short_case_lookup() -> None:
    assert ChatRequest(message="1").message == "1"


def test_chat_handles_empty_context_and_greetings(monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "retrieve_cases", lambda _: [])

    # Test greeting when no documents retrieved
    greeting_resp = pipeline.answer_query("hello")
    assert greeting_resp.citations == []
    assert "Hello" in greeting_resp.answer or "I can only answer" in greeting_resp.answer

    # Test irrelevant query when no documents retrieved
    irrelevant_resp = pipeline.answer_query("what is the weather today?")
    assert irrelevant_resp.citations == []
    assert irrelevant_resp.answer == "I can only answer questions related to the uploaded documents. Could you please rephrase your question?"

