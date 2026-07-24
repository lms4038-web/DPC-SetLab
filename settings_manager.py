from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any
from collections.abc import Mapping

SETTINGS_DIR = Path("config")
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
LEGACY_FILE = Path("config.json")

DEFAULT_SETTINGS: dict[str, Any] = {
    "spotify": {"client_id": "", "redirect_uri": "http://127.0.0.1:8888/callback"},
    "lastfm": {"api_key": ""},
    "discogs": {"token": ""},
    "preferences": {
        "playlist_name": "DPC DJ Set",
        "public_playlist": False,
        "auto_connect": True,
    },
}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _legacy_to_settings(legacy: dict[str, Any]) -> dict[str, Any]:
    return {
        "spotify": {"client_id": str(legacy.get("client_id", "")), "redirect_uri": "http://127.0.0.1:8888/callback"},
        "lastfm": {"api_key": str(legacy.get("lastfm_api_key", ""))},
        "discogs": {"token": str(legacy.get("discogs_token", ""))},
        "preferences": {
            "playlist_name": str(legacy.get("playlist_name", "DPC DJ Set")),
            "public_playlist": bool(legacy.get("public", False)),
            "auto_connect": True,
        },
    }


def load_settings(streamlit_secrets: Any | None = None) -> dict[str, Any]:
    settings = deepcopy(DEFAULT_SETTINGS)

    if SETTINGS_FILE.exists():
        settings = _merge(settings, _load_json(SETTINGS_FILE))
    elif LEGACY_FILE.exists():
        settings = _merge(settings, _legacy_to_settings(_load_json(LEGACY_FILE)))

    # Streamlit Cloud secrets and environment variables override local values.
    try:
        secrets = dict(streamlit_secrets or {})
    except Exception:
        secrets = {}

    spotify_secret = dict(secrets.get("spotify", {})) if isinstance(secrets.get("spotify", {}), Mapping) else {}
    lastfm_secret = dict(secrets.get("lastfm", {})) if isinstance(secrets.get("lastfm", {}), Mapping) else {}
    discogs_secret = dict(secrets.get("discogs", {})) if isinstance(secrets.get("discogs", {}), Mapping) else {}

    settings["spotify"]["client_id"] = (
        os.getenv("SPOTIFY_CLIENT_ID")
        or spotify_secret.get("client_id")
        or settings["spotify"].get("client_id", "")
    )
    settings["spotify"]["redirect_uri"] = (
        os.getenv("SPOTIFY_REDIRECT_URI")
        or spotify_secret.get("redirect_uri")
        or settings["spotify"].get("redirect_uri", "http://127.0.0.1:8888/callback")
    )
    settings["lastfm"]["api_key"] = (
        os.getenv("LASTFM_API_KEY")
        or lastfm_secret.get("api_key")
        or settings["lastfm"].get("api_key", "")
    )
    settings["discogs"]["token"] = (
        os.getenv("DISCOGS_TOKEN")
        or discogs_secret.get("token")
        or settings["discogs"].get("token", "")
    )
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(_merge(DEFAULT_SETTINGS, settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def has_required_keys(settings: dict[str, Any]) -> bool:
    return bool(
        str(settings.get("spotify", {}).get("client_id", "")).strip()
        and str(settings.get("lastfm", {}).get("api_key", "")).strip()
    )
