from pathlib import Path

import settings_manager as sm


def test_save_and_load_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sm, "SETTINGS_DIR", Path("config"))
    monkeypatch.setattr(sm, "SETTINGS_FILE", Path("config/settings.json"))
    monkeypatch.setattr(sm, "LEGACY_FILE", Path("config.json"))
    value = {
        "spotify": {"client_id": "abc"},
        "lastfm": {"api_key": "xyz"},
        "preferences": {"auto_connect": False},
    }
    sm.save_settings(value)
    loaded = sm.load_settings()
    assert loaded["spotify"]["client_id"] == "abc"
    assert loaded["lastfm"]["api_key"] == "xyz"
    assert loaded["preferences"]["auto_connect"] is False
    assert loaded["preferences"]["playlist_name"] == "DPC DJ Set"


def test_environment_overrides_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sm, "SETTINGS_DIR", Path("config"))
    monkeypatch.setattr(sm, "SETTINGS_FILE", Path("config/settings.json"))
    monkeypatch.setattr(sm, "LEGACY_FILE", Path("config.json"))
    sm.save_settings({"spotify": {"client_id": "file-id"}})
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "env-id")
    assert sm.load_settings()["spotify"]["client_id"] == "env-id"
