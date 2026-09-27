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


def _synthesize_answer(query: str, cases: list[RetrievedCase], amharic: bool, model=None) -> str:
    """Synthesize a coherent, direct legal answer from retrieved cases using LLM or structured summary fallback."""
    if not cases:
        return "ለቀረበው ጥያቄ አግባብነት ያለው የሰበር ውሳኔ አልተገኘም።" if amharic else "No relevant cassation decision precedents were found for this inquiry."

    if settings.google_api_key and model is not None:
        try:
            context_blocks = []
            for i, c in enumerate(cases, 1):
                c_num = c.metadata.get("case_number", "N/A")
                vol = c.metadata.get("volume", "")
                excerpt = c.content[:2000]
                context_blocks.append(f"[መዝገብ ቁጥር {c_num} ({vol})]\n{excerpt}")

            context_str = "\n\n".join(context_blocks)

            system_prompt = (
                "እርስዎ የኢትዮጵያ ፌዴራል ጠቅላይ ፍርድ ቤት የሰበር ችሎት የሕግ ባለሙያ ነዎት። "
                "ከተሰጡት የሰበር መዛግብት (ከታች የቀረቡት) ብቻ በመጠቀም ለቀረበው የሕግ ጥያቄ ቀጥተኛ፣ ግልጽ እና አጠቃላይ ሕጋዊ ምላሽ በአማርኛ ይጻፉ። "
                "የቀረቡት መዛግብት ቁጥር (ለምሳሌ መዝገብ ቁጥር ...) በምላሹ ውስጥ በግልጽ ይጠቅሱ።"
                if amharic
                else "You are a legal scholar on Ethiopian Supreme Court Cassation Division precedents. "
                "Using ONLY the provided case records below, synthesize a clear, comprehensive answer addressing the user query. "
                "Explicitly cite the relevant Case/File Numbers in your explanation."
            )

            prompt = f"{system_prompt}\n\n[የተገኙ የሰበር መዛግብት / RETRIEVED CASE RECORDS]:\n{context_str}\n\n[ተጠቃሚ ጥያቄ / USER QUERY]: {query}"
            response = model.invoke(prompt)
            answer_text = str(response.content).strip()
            if answer_text:
                return answer_text
        except Exception as e:
            print(f"LLM synthesis failed/timed out ({e}), falling back to structured synthesis.")

    # Fallback synthesis if LLM is unavailable
    if amharic:
        summary_lines = [f"ለቀረበው ጥያቄ ({query}) የተገኙ የሰበር ውሳኔ መዛግብት እንደሚከተለው ቀርበዋል።"]
        for c in cases:
            c_num = c.metadata.get("case_number", "N/A")
            vol = c.metadata.get("volume", "")
            summary_lines.append(f"• መዝገብ ቁጥር {c_num} ({vol})፦ {_extract_decision(c.content)[:300]}")
        return "\n".join(summary_lines)
    else:
        summary_lines = [f"Based on your query '{query}', the following precedent records were retrieved:"]
        for c in cases:
            c_num = c.metadata.get("case_number", "N/A")
            summary_lines.append(f"• Cassation File No. {c_num}: {_extract_decision(c.content)[:300]}")
        return "\n".join(summary_lines)


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
                timeout=7,
            )
        except Exception:
            model = None

    synthesized_answer = _synthesize_answer(normalized, cases, amharic, model=model)

    citations = [
        Citation(
            file_number=case.metadata.get("case_number", ""),
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
        answer=synthesized_answer,
        citations=citations,
        disclaimer="Research aid only. Confirm the complete ruling and binding status in the official Federal Supreme Court reporter.",
    )
