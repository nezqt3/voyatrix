import pytest
from pydantic import ValidationError

from app.core import config


def test_settings_read_bot_token_and_csv_dir_from_env(monkeypatch, tmp_path):
    config.get_settings.cache_clear()
    monkeypatch.setenv("BOT_TOKEN", "123456:ABC")
    monkeypatch.setenv("CSV_DIR", str(tmp_path))
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media-root"))

    settings = config.get_settings()

    assert settings.bot_token == "123456:ABC"
    assert settings.csv_dir == tmp_path
    assert settings.media_root == tmp_path / "media-root"

    config.get_settings.cache_clear()


def test_settings_build_render_webhook_url(monkeypatch):
    config.get_settings.cache_clear()
    monkeypatch.setenv("BOT_TOKEN", "123456:ABC")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://travel-bot.onrender.com/")
    monkeypatch.setenv("WEBHOOK_SECRET", "safe_test_secret")
    monkeypatch.setenv("PORT", "10000")

    settings = config.get_settings()

    assert settings.public_base_url == "https://travel-bot.onrender.com/"
    assert settings.webhook_url == (
        "https://travel-bot.onrender.com/telegram/webhook"
    )
    assert settings.port == 10000

    config.get_settings.cache_clear()


def test_settings_reject_invalid_webhook_secret():
    with pytest.raises(ValidationError, match="WEBHOOK_SECRET"):
        config.Settings(
            bot_token="123456:ABC",
            webhook_secret="invalid secret!",
        )
