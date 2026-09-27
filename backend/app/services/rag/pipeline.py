"""RAG orchestration: query, retrieval, and generation.

This module intentionally keeps the API independent of a particular LLM or vector
provider.  The sample corpus is a development fallback until official source
documents are ingested into the retrieval store.
"""

from app.schemas.chat import ChatResponse, Citation


DEVELOPMENT_CITATION = Citation(
    file_number="178204",
    title="Commercial Bank of Ethiopia v. Ato Girma Tesfaye",
    volume="Volume 21",
    page="142",
    bench="5 Justices Bench",
)


def answer_query(message: str, language: str = "auto") -> ChatResponse:
    """Return a stable response shape for the client while retrieval is configured.

    Do not represent the development fixture as an official holding.  A production
    retriever can replace this function without changing the HTTP contract.
    """
    normalized = " ".join(message.split())
    is_amharic = language == "am" or (language == "auto" and any("\u1200" <= char <= "\u137f" for char in normalized))
    answer = (
        "ይህ ምላሽ ለምርምር የተዘጋጀ የልማት ምሳሌ ነው። ኦፊሴላዊ የሰበር ውሳኔዎች "
        "ከተጫኑ በኋላ ስርዓቱ ተዛማጅ ሰነዶችን እና የተረጋገጡ ጥቅሶችን ያሳያል።"
        if is_amharic
        else "This is a development research response. Once official cassation "
        "materials are ingested, the system will return retrieved passages and "
        "verifiable citations matched to your query."
    )
    return ChatResponse(
        query=normalized,
        answer=answer,
        citations=[DEVELOPMENT_CITATION],
        disclaimer="For judicial research only. Verify every citation against the official Federal Supreme Court reporter.",
    )
