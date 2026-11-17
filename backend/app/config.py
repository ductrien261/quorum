from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  # repo root (quorum/)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", ROOT / "backend" / ".env"), extra="ignore")

    database_url: str = f"sqlite:///{(ROOT / 'data' / 'quorum.db').as_posix()}"
    artifact_dir: str = str(ROOT / "artifacts" / "vn")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    chat_max_tool_rounds: int = 5
    chat_history_turns: int = 10
    chat_rate_limit_per_hour: int = 60

    jwt_secret: str = "doi-chuoi-bi-mat-nay-trong-file-env-truoc-khi-dung"
    jwt_expire_days: int = 7

    cors_origins: str = "http://localhost:3000"
    timezone: str = "Asia/Ho_Chi_Minh"
    run_scheduler: bool = False  # start APScheduler inside the API process
    price_history_start: str = "2024-01-01"
    news_enabled: bool = True
    hf_offline: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def _db_default(cls, v):
        return v or f"sqlite:///{(ROOT / 'data' / 'quorum.db').as_posix()}"

    @field_validator("artifact_dir", mode="before")
    @classmethod
    def _art_default(cls, v):
        return v or str(ROOT / "artifacts" / "vn")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
