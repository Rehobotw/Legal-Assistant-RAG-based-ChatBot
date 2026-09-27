from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8")

    app_env: str = "development"
    database_url: str = "sqlite:///./app.db"
    jwt_secret_key: str = "replace-me"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str | None = None
    google_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_model: str = "gemini-2.5-flash"
    rag_data_dir: str = str(BACKEND_DIR / "data/raw")
    chroma_persist_directory: str = str(BACKEND_DIR / "data/chroma")
    chroma_collection_name: str = "fsc_labor_pension_am"
    rag_top_k: int = 5

settings = Settings()
