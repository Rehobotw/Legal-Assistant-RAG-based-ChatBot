import re

from app.core.config import settings
from app.schemas.chat import ChatResponse, Citation
from app.services.rag.retriever import RetrievedCase, retrieve_cases


class QuotaExceededError(RuntimeError):
    """Raised when an LLM or Embedding API quota / credit balance is exhausted."""


def is_quota_error(e: Exception) -> bool:
    """Check if an exception is caused by API credit balance exhaustion or rate limit / quota limits."""
    err_str = str(e).lower()
    quota_keywords = [
        "resource_exhausted",
        "resourceexhausted",
        "insufficient_quota",
        "credit_balance_exhausted",
        "quota exceeded",
        "you exceeded your current quota",
        "you have no credits remaining",
        "rate_limit_exceeded",
        "ratelimiterror",
        "googleratelimiterror",
        "429",
    ]
    return any(keyword in err_str for keyword in quota_keywords)


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



def _strip_procedural_noise(text: str) -> str:
    """
    Strip raw text verbatim noise, signature notes, page markers, scanner artifacts,
    and layout metadata to focus the LLM on substantive legal content.
    """
    if not text:
        return ""
    
    # Remove chunk headers
    text = re.sub(r"\[መዝገብ ቁጥር:[^\]]+\]", "", text)
    text = re.sub(r"\[Case No\.[^\]]+\]", "", text, flags=re.IGNORECASE)
    
    # Remove PAGE markers - all variations
    text = re.sub(r"---+\s*PAGE\s+\d+\s*---+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"PAGE\s+\d+(?:\s+\([^)]+\))?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"ገጽ\s*[:፡]?\s*\d+", "", text)
    
    # Remove signature noise variations
    text = re.sub(r"የማይነበብ(?:\s*የ[^\n]+)?\s*ፊርማ(?:\s*አለበት)?", "", text)
    text = re.sub(r"የዳኞች\s*ፊርማ\s*", "", text)
    text = re.sub(r"የ\s*\d+\s*ዳኞች\s*ፊርማ\s*አለበት", "", text)
    text = re.sub(r"unreadable\s*signature", "", text, flags=re.IGNORECASE)
    
    # Remove repeated dashes, underscores, equals signs
    text = re.sub(r"[-_=]{3,}", "", text)
    
    # Remove common OCR artifacts
    text = re.sub(r"\s*\[OCR\s*Error\][^\n]*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\[Illegible\][^\n]*", "", text, flags=re.IGNORECASE)
    
    # Remove isolated punctuation lines
    text = re.sub(r"^\s*[፡።፣፤፥፦፧፨]+\s*$", "", text, flags=re.MULTILINE)
    
    # Normalize whitespace - preserve paragraph structure
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lines = [line for line in lines if len(line) >= 2]
    result = "\n".join(lines)
    result = re.sub(r"^\s*[፡።፣፤፥፦፧፨\.\,\)\s]+", "", result)
    return result.strip()


def get_llm_models() -> list:
    """Return a prioritized list of available LLM instances (Gemini, NVIDIA, OpenAI) for seamless failover."""
    models = []
    provider_pref = (settings.llm_provider or "auto").lower()

    # 1. Google Gemini (High accuracy for Amharic legal synthesis)
    if settings.google_api_key and (provider_pref in ("gemini", "auto")):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            models.append(
                ChatGoogleGenerativeAI(
                    model=settings.gemini_model,
                    google_api_key=settings.google_api_key,
                    temperature=0,
                    max_retries=1,
                    timeout=15,
                )
            )
        except Exception as e:
            print(f"Failed to initialize Gemini LLM: {e}")

    # 2. NVIDIA API Key
    if settings.nvidia_api_key and (provider_pref in ("nvidia", "auto")):
        try:
            from langchain_openai import ChatOpenAI
            models.append(
                ChatOpenAI(
                    model=settings.nvidia_model,
                    api_key=settings.nvidia_api_key,
                    base_url=settings.nvidia_base_url,
                    temperature=0,
                    max_retries=1,
                    timeout=15,
                )
            )
        except Exception as e:
            print(f"Failed to initialize NVIDIA LLM: {e}")

    # 3. OpenAI API Key
    if settings.openai_api_key and (provider_pref in ("openai", "auto")):
        try:
            from langchain_openai import ChatOpenAI
            models.append(
                ChatOpenAI(
                    model="gpt-4o-mini",
                    api_key=settings.openai_api_key,
                    temperature=0,
                    max_retries=1,
                    timeout=15,
                )
            )
        except Exception as e:
            print(f"Failed to initialize OpenAI LLM: {e}")

    return models


def get_llm_model():
    """Backward compatibility helper returning primary LLM instance."""
    models = get_llm_models()
    return models[0] if models else None


def _holding(case: RetrievedCase, amharic: bool, model=None) -> str:
    """Summarize legal holding with strict length and timeout, falling back gracefully."""
    cleaned_content = _strip_procedural_noise(case.content)
    if model is None:
        return _extract_decision(cleaned_content)

    try:
        instruction = (
            "ከተሰጠው የሰበር ውሳኔ ብቻ በመጠቀም የዋናውን የሕግ ይዞታ በ2 አጭር ሐረጎች አጠቃልል።"
            if amharic
            else "Using only the supplied decision, summarize its holding in two short sentences."
        )
        decision_index = cleaned_content.rfind("ውሳኔ")
        source_excerpt = cleaned_content[decision_index:] if decision_index >= 0 else cleaned_content
        response = model.invoke(f"{instruction}\n\nCASE RECORD:\n{source_excerpt[:2500]}")
        return str(response.content).strip()
    except Exception as e:
        if is_quota_error(e):
            raise QuotaExceededError("You are out of API credits or quota has been exceeded.") from e
        print(f"Gemini API invocation failed/timed out ({e}), using direct extraction fallback.")
        return _extract_decision(cleaned_content)


def _extract_decision(content: str) -> str:
    """A transparent, source-only fallback when LLM is slow, unavailable, or rate limited."""
    cleaned = _strip_procedural_noise(content)
    
    # Find the decision section (first occurrence of ውሳኔ heading)
    decision_index = cleaned.find("ውሳኔ")
    if decision_index >= 0:
        excerpt = cleaned[decision_index:]
    else:
        excerpt = cleaned
    
    # Remove leading heading 'ውሳኔ' if present at start
    excerpt = re.sub(r"^\s*ውሳኔ\s*[:፡]?\s*", "", excerpt)
    
    # Remove common noise patterns that might remain
    excerpt = re.sub(r"(?:PAGE|ገጽ)\s*\d+", "", excerpt, flags=re.IGNORECASE)
    excerpt = re.sub(r"\([^)]*Content\s*Page[^)]*\)", "", excerpt, flags=re.IGNORECASE)
    
    # Join and limit
    words = excerpt.split()
    return " ".join(words)[:500].strip()


def _format_context(cases: list[RetrievedCase]) -> str:
    """Group retrieved chunks by document/case number, strip procedural noise, and format context for LLM."""
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
        sanitized_texts = [_strip_procedural_noise(c.content) for c in case_list]
        combined_text = "\n\n".join(t for t in sanitized_texts if t)
        formatted_blocks.append(f"{header}\n{combined_text}")

    return "\n\n".join(formatted_blocks)


def _synthesize_answer(query: str, cases: list[RetrievedCase], amharic: bool, model=None) -> str:
    """Synthesize a comprehensive legal answer using LLM with proper source citations."""
    default_fallback_response = "I can only answer questions related to the uploaded documents. Could you please rephrase your question?"

    if not cases:
        return default_fallback_response

    context_str = _format_context(cases)
    if not context_str or len(context_str.strip()) < 30:
        return default_fallback_response

    candidate_models = [model] if model is not None else get_llm_models()

    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    # Build source citations for the LLM to reference
    source_info = []
    for c in cases:
        c_num = c.metadata.get("case_number", "N/A")
        vol = c.metadata.get("volume", "")
        start_page = c.metadata.get("start_page", c.metadata.get("page_number", c.metadata.get("page", "N/A")))
        end_page = c.metadata.get("end_page", start_page)
        page_range = f"{start_page}-{end_page}" if str(start_page) != str(end_page) else str(start_page)
        court = c.metadata.get("court", "Federal Supreme Court Cassation Division")
        
        if amharic:
            source_info.append(f"መዝገብ ቁጥር፦ {c_num}, ቅጽ፦ {vol if vol else 'N/A'}, ገጾች፦ {page_range}, ፍርድ ቤት፦ {court}")
        else:
            source_info.append(f"Case No: {c_num}, Volume: {vol if vol else 'N/A'}, Pages: {page_range}, Court: {court}")
    
    sources_text = "\n".join(f"- {s}" for s in source_info)

    system_instruction = (
        "You are an expert Ethiopian Federal Supreme Court Cassation Division legal analyst.\n"
        "Your objective is to read the full context of a legal decision across all pages and write a comprehensive, "
        "logically structured Amharic legal summary.\n\n"

        "## CRITICAL SYNTHESIS REQUIREMENTS:\n"
        "1. **NEVER output raw text quotes, unformatted source chunks, procedural noise, or signature blocks.** Synthesize an original, professional response.\n"
        "2. **DO NOT repeat the case number or volume in a header at the start.** Begin directly with the substantive legal analysis.\n"
        "3. Carefully analyze the text across all pages to extract:\n"
        "   * The original dispute (e.g., illegal termination, property damage, contract breach)\n"
        "   * The decision of the First Instance Court (የፌዴራል የመጀመሪያ ደረጃ ፍርድ ቤት ውሳኔ) including legal proclamations cited (e.g. አዋጅ ቁጥር 377/96), statute of limitations (ይርጋ), monetary awards, and legal reasoning\n"
        "   * The position of the High Court / Appellate Court (if applicable)\n"
        "   * The Cassation Division legal interpretation & final holding (የሰበር ችሎት ውሳኔ)\n\n"
        "4. Structure your response using clean, bolded sections:\n"
        "   * **የክርክሩ መነሻ ፍሬ ነገር (Case Background & Dispute)**\n"
        "   * **የስር ፍርድ ቤት ውሳኔ (Lower Court Decision & Compensation)**\n"
        "   * **የከፍተኛ ፍርድ ቤት አቋም (High Court Position)** (if applicable)\n"
        "   * **የሰበር ችሎት የህግ ትርጉም እና ውሳኔ (Cassation Court Legal Interpretation & Holding)**\n\n"
        "5. At the end of your response, add a **Sources** section listing all relevant source citations provided below.\n"
        "6. When the question asks about a specific case number, focus ONLY on that case and provide comprehensive details from all available pages."
    )

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_instruction),
        ("user", "Context Provided:\n{formatted_context}\n\nAvailable Sources:\n{sources}\n\nUser Question: {user_query}"),
    ])

    for m in candidate_models:
        if m is None:
            continue
        try:
            chain = prompt_template | m | StrOutputParser()
            result = chain.invoke({"formatted_context": context_str, "sources": sources_text, "user_query": query})
            answer_text = str(result).strip()
            if answer_text and len(answer_text) > 50:
                return answer_text
        except Exception as e:
            if is_quota_error(e):
                print(f"⚠️ Provider quota exceeded ({e}). Trying next model...")
            else:
                print(f"⚠️ LLM provider call failed ({e}). Trying next model...")

    # If all LLM providers fail, return a user-friendly message rather than raw text
    if amharic:
        return (
            "ይቅርታ፣ አሁን ለጊዜው ምርምር አገልግሎቱ የማይገኝ ይመስላል። እባክዎ ቆይተው እንደገና ይሞክሩ።\n\n"
            f"**ምንጮች፦**\n{sources_text}"
        )
    else:
        return (
            "Apologies, the research service is temporarily unavailable. Please try again in a moment.\n\n"
            f"**Sources:**\n{sources_text}"
        )



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
    except Exception as error:
        if is_quota_error(error):
            quota_msg = (
                "⚠️ የኤፒአይ ክሬዲት አልቋል (ወይም ኮታ ተሟጧል)። እባክዎን የብድር ሂሳብዎን (OpenAI / Google) ያረጋግጡ።"
                if amharic else
                "⚠️ You are out of API credits (or your quota limit has been exceeded). Please check your OpenAI / Google API billing or quota to continue."
            )
            return ChatResponse(
                query=normalized,
                answer=quota_msg,
                citations=[],
                disclaimer="API Quota / Credit Exhausted.",
            )
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

    # Instantiate model using configured provider (NVIDIA, Gemini, OpenAI)
    try:
        model = get_llm_model()
    except QuotaExceededError:
        quota_msg = (
            "⚠️ የኤፒአይ ክሬዲት አልቋል (ወይም ኮታ ተሟጧል)። እባክዎን የብድር ሂሳብዎን ያረጋግጡ።"
            if amharic else
            "⚠️ You are out of API credits (or your quota limit has been exceeded). Please check your API billing or quota to continue."
        )
        return ChatResponse(
            query=normalized,
            answer=quota_msg,
            citations=[],
            disclaimer="API Quota / Credit Exhausted.",
        )

    try:
        synthesized_answer = _synthesize_answer(normalized, cases, amharic, model=model)

        citations = []
        for rank, case in enumerate(cases, start=1):
            start_page = case.metadata.get("start_page", case.metadata.get("page_number", case.metadata.get("page", "")))
            end_page = case.metadata.get("end_page", start_page)
            
            # Format page range display
            if start_page and end_page and str(start_page) != str(end_page):
                page_display = f"Pages {start_page}-{end_page}"
            elif start_page:
                page_display = f"Page {start_page}"
            else:
                page_display = ""
            
            citation = Citation(
                case_number=str(case.metadata.get("case_number", "")),
                file_number=str(case.metadata.get("case_number", "")),
                volume=str(case.metadata.get("volume", "")),
                page_number=str(start_page),
                page=str(start_page),
                start_page=str(start_page),
                end_page=str(end_page),
                similarity_score=round(case.score, 4),
                score=round(case.score, 4),
                match_type=getattr(case, "match_type", "semantic"),
                source_filename=str(case.metadata.get("source_filename", case.metadata.get("source_file", ""))),
                source_file=str(case.metadata.get("source_file", case.metadata.get("source_filename", ""))),
                date=str(case.metadata.get("date", "")),
                court=str(case.metadata.get("court", "Federal Supreme Court Cassation Division")),
                holding=_holding(case, amharic, model=model),
                rank=rank,
                bench=page_display,
            )
            citations.append(citation)

        return ChatResponse(
            query=normalized,
            answer=synthesized_answer,
            citations=citations,
            disclaimer="Research aid only. Confirm the complete ruling and binding status in the official Federal Supreme Court reporter.",
        )
    except Exception as e:
        if is_quota_error(e) or isinstance(e, QuotaExceededError):
            quota_msg = (
                "⚠️ የኤፒአይ ክሬዲት አልቋል (ወይም ኮታ ተሟጧል)። እባክዎን የብድር ሂሳብዎን (OpenAI / Google) ያረጋግጡ።"
                if amharic else
                "⚠️ You are out of API credits (or your quota limit has been exceeded). Please check your OpenAI / Google API billing or quota to continue."
            )
            return ChatResponse(
                query=normalized,
                answer=quota_msg,
                citations=[],
                disclaimer="API Quota / Credit Exhausted.",
            )
        raise e



