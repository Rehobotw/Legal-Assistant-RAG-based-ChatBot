"""Grounded RAG query pipeline; every legal statement is attached to a case."""

from app.core.config import settings
from app.schemas.chat import ChatResponse, Citation
from app.services.rag.retriever import RetrievedCase, retrieve_cases


def _is_amharic(message: str, language: str) -> bool:
    return language == "am" or (language == "auto" and any("\u1200" <= char <= "\u137f" for char in message))


def _holding(case: RetrievedCase, amharic: bool, model=None) -> str:
    """Summarize legal holding with strict length and timeout, falling back gracefully."""
    if not settings.google_api_key or model is None:
        return _extract_decision(case.content)

    try:
        instruction = (
            "ከተሰጠው የሰበር ውሳኔ ብቻ በመጠቀም የዋናውን የሕግ ይዞታ በ2 አጭር ሐረጎች አጠቃልል።"
            if amharic
            else "Using only the supplied decision, summarize its holding in two short sentences."
        )
        decision_index = case.content.rfind("ውሳኔ")
        source_excerpt = case.content[decision_index:] if decision_index >= 0 else case.content
        response = model.invoke(f"{instruction}\n\nCASE RECORD:\n{source_excerpt[:2500]}")
        return str(response.content).strip()
    except Exception as e:
        print(f"Gemini API invocation failed/timed out ({e}), using direct extraction fallback.")
        return _extract_decision(case.content)


def _extract_decision(content: str) -> str:
    """A transparent, source-only fallback when Gemini is slow, unavailable, or rate limited."""
    decision_index = content.rfind("ውሳኔ")
    excerpt = content[decision_index:] if decision_index >= 0 else content
    return " ".join(excerpt.split())[:500]


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

    # Instantiate model once for the request if API key is present
    model = None
    if settings.google_api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            model = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.google_api_key,
                temperature=0,
                max_retries=1,
                timeout=5,
            )
        except Exception:
            model = None

    citations = [
        Citation(
            file_number=case.metadata["case_number"],
            date=case.metadata.get("date", ""),
            court=case.metadata.get("court", "Federal Supreme Court Cassation Division"),
            holding=_holding(case, amharic, model=model),
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
