"""HuggingFace embedding client used by the Chroma corpus."""


def get_embeddings():
    """Create the local HuggingFace embedding client on demand."""
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

