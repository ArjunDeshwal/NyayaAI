from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NYAYAI_API_", env_file=".env")

    artifacts_dir: Path = Field(default=Path("/tmp/nyayai-artifacts"))
    max_upload_mb: int = 25
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5000",
            "http://localhost:8080",
            "https://nyaya-494216.web.app",
            "https://nyaya-494216.firebaseapp.com",
            "https://nyayai.app",
            "https://www.nyayai.app",
        ]
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return _settings
