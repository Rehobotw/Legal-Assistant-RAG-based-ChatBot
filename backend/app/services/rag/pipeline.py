"""Grounded RAG query pipeline; every legal statement is attached to a case."""

from app.core.config import settings
from app.schemas.chat import ChatResponse, Citation
from app.services.rag.retriever import RetrievedCase, retrieve_cases


def _is_amharic(message: str, language: str) -> bool:
    return language == "am" or (language == "auto" and any("\u1200" <= char <= "\u137f" for char in message))


def _holding(case: RetrievedCase, amharic: bool) -> str:
    """Use Gemini only to summarize this one record, never across records."""
    if not settings.google_api_key:
        return _extract_decision(case.content)
    from langchain_google_genai import ChatGoogleGenerativeAI

    instruction = (
        "ከተሰጠው የሰበር ውሳኔ ብቻ በመጠቀም የዋናውን የሕግ ይዞታ በ2 አጭር ሐረጎች "
        "አጠቃልል። ውሳኔው የማይደግፈውን አትጨምር።"
        if amharic
        else "Using only the supplied cassation decision, summarize its holding in two short sentences. Do not add facts or legal conclusions not supported by the record."
    )
    model = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.google_api_key, temperature=0)
    response = model.invoke(f"{instruction}\n\nCASE RECORD:\n{case.content[:6000]}")
    return str(response.content).strip()


def _extract_decision(content: str) -> str:
    """A transparent, source-only fallback when Gemini is not configured."""
    decision_index = content.rfind("ውሳኔ")
    excerpt = content[decision_index:] if decision_index >= 0 else content
    return " ".join(excerpt.split())[:700]


def answer_query(message: str, language: str = "auto") -> ChatResponse:
    normalized = " ".join(message.split())
    amharic = _is_amharic(normalized, language)
    try:
        cases = retrieve_cases(normalized)
    except (ImportError, RuntimeError) as error:
        return ChatResponse(
            query=normalized,
            answer=("የውሳኔ መረጃ ጠቋሚው ገና አልተዘጋጀም።" if amharic else "The precedent index is not ready yet."),
            citations=[],
            disclaimer=str(error),
        )

    citations = [
        Citation(
            file_number=case.metadata["case_number"],
            date=case.metadata.get("date", ""),
            court=case.metadata.get("court", "Federal Supreme Court Cassation Division"),
            holding=_holding(case, amharic),
            rank=rank,
            score=round(case.score, 4),
            volume=case.metadata.get("volume", ""),
            page=case.metadata.get("page", ""),
        )
        for rank, case in enumerate(cases, start=1)
    ]
    return ChatResponse(
        query=normalized,
        answer=("የተገኙ የሰበር ውሳኔዎች፤ እያንዳንዱ ማጠቃለያ ከራሱ መዝገብ ጋር ተያይዟል።" if amharic else "Retrieved cassation decisions. Each summary is tied to its own source record."),
        citations=citations,
        disclaimer="Research aid only. Confirm the complete ruling and binding status in the official Federal Supreme Court reporter.",
    )
