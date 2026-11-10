from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "CiviSeva - KMRL AI Grievance Redressal System"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./civiseva.db"
    SAFE_KEY: str = "KMRL-SECURE-2026"
    GOOGLE_API_KEY: str = "AIzaSyDfPQsDsc1N485Ixe1p9sUx0xUAyS0KoTc"
    KMRL_BASE_PATH: str = str(BASE_DIR)
    KMRL_MODEL_PATH: str = str(BASE_DIR / "data" / "model" / "document_classifier.joblib")
    KMRL_CHROMA_PATH: str = str(BASE_DIR / "data" / "chroma_db")
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
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

