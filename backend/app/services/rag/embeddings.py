"""OpenAI embedding client used by the Chroma corpus."""

from app.core.config import settings


def get_embeddings():
    """Create the configured OpenAI text-embedding-3 client on demand."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to build or query the precedent index.")

    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )
