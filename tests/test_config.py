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
