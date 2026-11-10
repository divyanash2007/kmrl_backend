import os
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BASE_DIR / ".env"), ".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "CiviSeva - KMRL AI Grievance Redressal System"
    API_V1_STR: str = "/api/v1"

    # Database: loaded from DATABASE_URL env var
    DATABASE_URL: str = "sqlite:///./civiseva.db"

    # Safe-Key Authentication: loaded from SAFE_KEY env var
    SAFE_KEY: str = "KMRL-SECURE-2026"

    # Google Gemini API Key: strictly loaded from GOOGLE_API_KEY env var (no hardcoded secret)
    GOOGLE_API_KEY: str = ""

    # ML & RAG Storage: loaded from env vars or defaults to repo data directory
    KMRL_BASE_PATH: str = str(BASE_DIR)
    KMRL_MODEL_PATH: str = str(BASE_DIR / "data" / "model" / "document_classifier.joblib")
    KMRL_CHROMA_PATH: str = str(BASE_DIR / "data" / "chroma_db")

    # Allowed CORS Origins: supports comma-separated string, JSON list, or list
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",
    ]

    @field_validator("KMRL_MODEL_PATH", "KMRL_CHROMA_PATH", mode="before")
    @classmethod
    def resolve_relative_paths(cls, v: str) -> str:
        """Resolve relative paths against BASE_DIR so env vars like 'data/...' work from any CWD."""
        if v:
            p = Path(v)
            if not p.is_absolute():
                return str((BASE_DIR / p).resolve())
            return str(p)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    @property
    def normalized_database_url(self) -> str:
        """
        Normalize database URL for Supabase / PostgreSQL.
        Converts postgres:// or postgresql:// to postgresql+psycopg://
        for compatibility with SQLAlchemy 2 and psycopg 3.
        """
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


settings = Settings()
