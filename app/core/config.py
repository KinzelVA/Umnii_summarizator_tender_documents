from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Tender Document Summarizer"
    app_version: str = "0.1.0"
    app_description: str = (
        "API for extracting structured information from tender documentation."
    )
    max_pdf_size_mb: int = Field(default=20, gt=0, le=100)

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:20b"
    llm_timeout_seconds: int = Field(default=120, gt=0, le=600)

    model_config = SettingsConfigDict(
        env_prefix="TENDER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def max_pdf_size_bytes(self) -> int:
        return self.max_pdf_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()