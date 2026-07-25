from __future__ import annotations

import os
import pickle
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Mapping, MutableMapping

_SESSION_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_DEFAULT_TTL_SEC = 60 * 60 * 24 * 7

# Only durable workflow data is stored. Streamlit widget internals and transient
# progress objects are deliberately excluded.
PERSISTENT_KEYS = {
    "spotify_web_token",
    "workspace_entered",
    "landing_started",
    "home_wizard_started",
    "wizard_mode",
    "wizard_target_tab",
    "raw_collection",
    "playlists",
    "source_type",
    "rekordbox_xml_bytes",
    "rekordbox_xml_name",
    "rekordbox_xml_health",
    "candidate_df",
    "candidate_source_playlist",
    "candidate_selection_signature",
    "online_enriched_df",
    "set_df",
    "set_revision",
    "build_settings",
    "performance_plan_settings",
    "build_target_minutes",
    "build_target_sec",
    "build_estimated_sec",
    "build_overlap_sec",
    "build_preset_label",
    "performance_context",
    "selected_genres",
    "selected_preset",
    "generate_review_complete",
    "generate_check_summary",
    "generate_check_flow",
    "generate_check_details",
    "set_edit_complete",
    "edit_check_open_close",
    "edit_check_bpm",
    "edit_check_vocal",
    "edit_check_path",
    "spotify_matches",
    "spotify_fill_tracks",
    "spotify_fill_tracks_edited",
    "spotify_export_complete",
    "spotify_playlist_url",
    "spotify_playlist_name",
    "rekordbox_export_complete",
    "rekordbox_playlist_name",
}


def new_session_id() -> str:
    return uuid.uuid4().hex


def is_valid_session_id(value: Any) -> bool:
    return bool(_SESSION_ID_RE.fullmatch(str(value or "").strip().lower()))


def _store_dir(root: Path | None = None) -> Path:
    directory = root or Path(tempfile.gettempdir()) / "dpc_setlab_sessions"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _session_path(session_id: str, root: Path | None = None) -> Path:
    if not is_valid_session_id(session_id):
        raise ValueError("Invalid DPC session id")
    return _store_dir(root) / f"{session_id}.pkl"


def build_snapshot(state: Mapping[str, Any]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for key in PERSISTENT_KEYS:
        if key in state:
            snapshot[key] = state[key]
    return snapshot


def save_snapshot(session_id: str, state: Mapping[str, Any], root: Path | None = None) -> None:
    path = _session_path(session_id, root)
    payload = {
        "version": 1,
        "saved_at": int(time.time()),
        "state": build_snapshot(state),
    }
    temp_path = path.with_suffix(f".{os.getpid()}.tmp")
    try:
        with temp_path.open("wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def load_snapshot(session_id: str, root: Path | None = None, ttl_sec: int = _DEFAULT_TTL_SEC) -> dict[str, Any]:
    path = _session_path(session_id, root)
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            payload = pickle.load(handle)
        saved_at = int(payload.get("saved_at", 0))
        if saved_at <= 0 or time.time() - saved_at > ttl_sec:
            path.unlink(missing_ok=True)
            return {}
        state = payload.get("state", {})
        return dict(state) if isinstance(state, dict) else {}
    except Exception:
        # A partial or incompatible snapshot must never prevent the app from opening.
        path.unlink(missing_ok=True)
        return {}


def restore_snapshot(session_id: str, state: MutableMapping[str, Any], root: Path | None = None) -> bool:
    restored = load_snapshot(session_id, root)
    if not restored:
        return False
    for key, value in restored.items():
        if key not in state:
            state[key] = value
    return True


def purge_expired(root: Path | None = None, ttl_sec: int = _DEFAULT_TTL_SEC) -> None:
    directory = _store_dir(root)
    cutoff = time.time() - ttl_sec
    for path in directory.glob("*.pkl"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError:
            continue
