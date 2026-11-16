import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env")


def _optional_positive_int(name: str) -> int | None:
    raw_value = os.getenv(name)
    if not raw_value:
        return None
    try:
        value = int(raw_value)
    except ValueError:
        return None
    return value if value > 0 else None


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    app_name: str = os.getenv("APP_NAME", "ResolveAI API")
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    database_url: str | None = os.getenv("DATABASE_URL")
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "2"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "1"))
    db_pool_recycle_seconds: int = int(
        os.getenv("DB_POOL_RECYCLE_SECONDS", "1800")
    )
    admin_username: str | None = os.getenv("ADMIN_USERNAME")
    admin_password_hash: str | None = os.getenv("ADMIN_PASSWORD_HASH")
    jwt_secret: str | None = os.getenv("JWT_SECRET")
    jwt_expiry_minutes: int | None = _optional_positive_int(
        "JWT_EXPIRY_MINUTES"
    )
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_generation_model: str = os.getenv(
        "GEMINI_GENERATION_MODEL", "gemini-3.5-flash-lite"
    )
    gemini_embedding_model: str = os.getenv(
        "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
    )
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))
    rag_chunk_token_limit: int = int(os.getenv("RAG_CHUNK_TOKEN_LIMIT", "1800"))
    rag_chunk_overlap_tokens: int = int(
        os.getenv("RAG_CHUNK_OVERLAP_TOKENS", "150")
    )
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "5"))
    rag_similarity_threshold: float | None = (
        float(os.getenv("RAG_SIMILARITY_THRESHOLD"))
        if os.getenv("RAG_SIMILARITY_THRESHOLD")
        else None
    )


settings = Settings()
