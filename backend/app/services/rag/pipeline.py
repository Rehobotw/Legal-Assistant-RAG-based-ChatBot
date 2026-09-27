import re

from app.core.config import settings
from app.schemas.chat import ChatResponse, Citation
from app.services.rag.retriever import RetrievedCase, retrieve_cases


def _is_amharic(message: str, language: str) -> bool:
    return language == "am" or (language == "auto" and any("\u1200" <= char <= "\u137f" for char in message))


def _is_casual_greeting(message: str) -> bool:
    """Detect non-legal casual inputs or standard greetings."""
    greetings = {
        "hi", "hello", "hey", "greetings", "good morning", "good afternoon",
        "good evening", "howdy", "ሰላም", "ሰላምታ", "ጤና ይስጥልኝ"
    }
    clean = re.sub(r"[^\w\s\u1200-\u137f]", "", message.strip().lower())
    return clean in greetings


def _is_context_sufficient(cases: list[RetrievedCase]) -> bool:
    """Evaluate whether retrieved context contains substantive legal facts/arguments."""
    if not cases:
        return False
    total_content_length = sum(len(c.content.strip()) for c in cases)
    return total_content_length >= 30



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


def _format_context(cases: list[RetrievedCase]) -> str:
    """Group retrieved chunks by document/case number to cleanly present the full legal narrative to the LLM."""
    if not cases:
        return "No context provided."

    grouped: dict[str, list[RetrievedCase]] = {}
    for c in cases:
        c_num = c.metadata.get("case_number", "Unknown")
        grouped.setdefault(c_num, []).append(c)

    formatted_blocks = []
    for c_num, case_list in grouped.items():
        vol = case_list[0].metadata.get("volume", "")
        vol_str = f" ({vol})" if vol else ""
        header = f"[መዝገብ ቁጥር፦ {c_num}{vol_str}]"
        combined_text = "\n\n".join(c.content for c in case_list)
        formatted_blocks.append(f"{header}\n{combined_text}")

    return "\n\n".join(formatted_blocks)


def _synthesize_answer(query: str, cases: list[RetrievedCase], amharic: bool, model=None) -> str:
    """Synthesize a direct legal answer from retrieved case context via LCEL chain or handle empty context/greetings."""
    default_fallback_response = "I can only answer questions related to the uploaded documents. Could you please rephrase your question?"

    if settings.google_api_key and model is not None:
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            context_str = _format_context(cases)

            system_instruction = (
                "You are an assistant answering questions based strictly on the provided context. "
                "If the user's query is a standard greeting, respond politely without using context. "
                "If the provided context is empty or does not contain the answer to the user's query, output EXACTLY: "
                "'I can only answer questions related to the uploaded documents. Could you please rephrase your question?' "
                "Do not attempt to guess or use outside knowledge.\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. LANGUAGE ALIGNMENT: You MUST respond in the exact same language as the user's query (Amharic or English).\n"
                "2. STRICT GROUNDING: Rely ONLY on the facts, dates, case numbers, and legal arguments provided in the CONTEXT. Do NOT fabricate information or rely on external knowledge.\n"
                "3. LEGAL SYNTHESIS & STRUCTURE:\n"
                "   - State the core legal dispute clearly.\n"
                "   - Explicitly identify and mention key details present in the context: Volume Number, Cassation File Number, Parties involved (Applicant/አመልካች and Respondent/ተጠሪ), specific dates, workplace roles, and applicable Proclamations (e.g., Proclamation No. 377/2003 or አዋጅ ቁጥር 377/96).\n"
                "   - Summarize the procedural facts and the specific legal error or jurisdictional question submitted to the Cassation Court in chronological order (Facts -> Legal Issue -> Arguments -> Court Reasoning -> Ruling).\n"
                "4. TERMINOLOGY: Use standard Ethiopian legal terminology appropriate for the output language (e.g., Material Jurisdiction / የሥረ ነገር ሥልጣን, Fundamental Error of Law / መሠረታዊ የሕግ ስህተት).\n"
                "5. FALLBACK: If the provided CONTEXT is empty or does not contain the answer to the user's query (and the query is not a standard greeting), output EXACTLY: "
                "'I can only answer questions related to the uploaded documents. Could you please rephrase your question?'\n"
                "   - If the context contains multiple different case numbers, YOU MUST IGNORE ALL OF THEM EXCEPT the specific case number requested in the user's query. Answer the question relying ONLY on the facts of the requested case."
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
            print(f"LLM chain synthesis failed ({e}), falling back to default handling.")

    if not cases:
        return default_fallback_response

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

    # 1. Intent Pre-Check / Routing for Casual Inputs
    if _is_casual_greeting(normalized):
        greeting_text = "ሰላም! እንዴት ልረዳዎት እችላለሁ?" if amharic else "Hello! How can I help you today with your legal precedent research?"
        return ChatResponse(
            query=normalized,
            answer=greeting_text,
            citations=[],
            disclaimer="Research aid only. Confirm the complete ruling and binding status in the official Federal Supreme Court reporter.",
        )

    # 2. Retrieve cases from Vector Store
    try:
        cases = retrieve_cases(normalized)
    except (ImportError, RuntimeError) as error:
        return ChatResponse(
            query=normalized,
            answer=("የውሳኔ መረጃ ጠቋሚው ገና አልተዘጋጀም።" if amharic else "The precedent index is not ready yet."),
            citations=[],
            disclaimer=str(error),
        )

    # 3. Context Sufficiency Check
    if not _is_context_sufficient(cases):
        fallback_text = "I can only answer questions related to the uploaded documents. Could you please rephrase your question?"
        return ChatResponse(
            query=normalized,
            answer=fallback_text,
            citations=[],
            disclaimer="Research aid only. Confirm the complete ruling and binding status in the official Federal Supreme Court reporter.",
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
                timeout=10,
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

