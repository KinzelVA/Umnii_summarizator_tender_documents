from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Tender Document Summarizer"
    app_version: str = "0.1.0"
    app_description: str = (
        "API for extracting structured information from tender documentation."
    )

    model_config = SettingsConfigDict(
        env_prefix="TENDER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()