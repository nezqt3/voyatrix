from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    bot_token: str
    csv_dir: Path = BASE_DIR / "aggregation" / "csv"
    media_root: Path = BASE_DIR / "aggregation" / "export"
    webhook_base_url: str | None = None
    render_external_url: str | None = None
    webhook_path: str = "/telegram/webhook"
    webhook_secret: str | None = None
    host: str = "0.0.0.0"
    port: int = 8080

    @field_validator("webhook_secret")
    @classmethod
    def validate_webhook_secret(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not 1 <= len(value) <= 256 or not all(
            character.isascii() and (character.isalnum() or character in "_-")
            for character in value
        ):
            raise ValueError(
                "WEBHOOK_SECRET must contain 1-256 ASCII letters, numbers, "
                "underscores, or hyphens"
            )
        return value

    @property
    def public_base_url(self) -> str | None:
        """Return an explicit URL locally or Render's assigned public URL."""
        return self.webhook_base_url or self.render_external_url

    @property
    def webhook_url(self) -> str | None:
        if not self.public_base_url:
            return None
        return f"{self.public_base_url.rstrip('/')}{self.webhook_path}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
