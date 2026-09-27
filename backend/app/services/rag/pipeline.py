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
    """Synthesize a single-paragraph, direct legal answer from retrieved case context via LCEL chain."""
    if not cases:
        return "ለቀረበው ጥያቄ አግባብነት ያለው የሰበር ውሳኔ አልተገኘም።" if amharic else "No relevant cassation decision precedents were found for this inquiry."

    if settings.google_api_key and model is not None:
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            context_blocks = []
            for c in cases:
                c_num = c.metadata.get("case_number", "N/A")
                vol = c.metadata.get("volume", "")
                context_blocks.append(f"[መዝገብ ቁጥር፦ {c_num} ({vol})]\n{c.content[:2500]}")

            context_str = "\n\n".join(context_blocks)

            system_instruction = (
                "እርስዎ የኢትዮጵያ ፌዴራል ጠቅላይ ፍርድ ቤት የሰበር ችሎት የሕግ ረዳት ነዎት። "
                "ከዚህ በታች ከተሰጡት የሰበር ውሳኔ መዛግብት (CONTEXT) ብቻ በመጠቀም ለቀረበው የሕግ ጥያቄ ቀጥተኛ፣ ግልጽ እና አጠቃላይ የሕግ ማጠቃለያ በ1 አጭር አንቀጽ በአማርኛ ይጻፉ። "
                "የተጠቀሱትን መዝገብ ቁጥሮች (ለምሳሌ መዝገብ ቁጥር 130665) እና የክርክሩን ዋና ጉዳይና ውሳኔ በምላሹ ውስጥ በግልጽ ያካቱ። "
                "ያልተጠቀሱ አዳዲስ ጭብጦችን አይፍጠሩ።"
                if amharic
                else "You are an Ethiopian Supreme Court Cassation Division legal assistant. "
                "Synthesize a direct, clear single-paragraph legal response strictly from the provided case CONTEXT. "
                "Explicitly cite case numbers (e.g. Case No. 130665) and summarize the core holding."
            )

            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_instruction),
                ("user", "CONTEXT:\n{context}\n\nQUESTION:\n{question}"),
            ])

            chain = prompt_template | model | StrOutputParser()
            result = chain.invoke({"context": context_str, "question": query})
            answer_text = str(result).strip()
            if answer_text:
                return answer_text
        except Exception as e:
            print(f"LLM chain synthesis failed ({e}), falling back to structured excerpt synthesis.")

    # Clean fallback synthesis if LLM key is missing or calls time out
    if amharic:
        summary_lines = []
        for c in cases:
            c_num = c.metadata.get("case_number", "N/A")
            vol = c.metadata.get("volume", "")
            summary_lines.append(f"በቅጽ {vol}፣ መዝገብ ቁጥር {c_num} የተመዘገበው የክርክሩ ዋና ጉዳይ፦ {_extract_decision(c.content)[:350]}")
        return " ".join(summary_lines)
    else:
        summary_lines = []
        for c in cases:
            c_num = c.metadata.get("case_number", "N/A")
            summary_lines.append(f"For Cassation Case No. {c_num}: {_extract_decision(c.content)[:350]}")
        return " ".join(summary_lines)


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
