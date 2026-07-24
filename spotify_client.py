from __future__ import annotations

import base64
import hashlib
import hmac
import http.server
import json
import re
import secrets
import threading
import time
import unicodedata
import urllib.parse
import webbrowser
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import requests

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"
LOCAL_REDIRECT_URI = "http://127.0.0.1:8888/callback"
REDIRECT_URI = LOCAL_REDIRECT_URI
SCOPES = "playlist-modify-private playlist-modify-public"
TOKEN_FILE = Path(".spotify_token.json")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).casefold().replace("&", " and ")
    text = re.sub(r"\b(feat|featuring|ft)\.?\b", " ", text)
    text = re.sub(r"[\(\)\[\]\{\}:;,.!?/'\"`~@#$%^*_+=|\\<>–—-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    result: dict[str, str] = {}

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _CallbackHandler.result = {"code": params["code"][0], "state": params.get("state", [""])[0]}
            message, status = "Spotify 연결이 완료됐습니다. DPC Set Builder 탭으로 돌아가세요.", 200
        else:
            _CallbackHandler.result = {"error": params.get("error", ["authorization_failed"])[0]}
            message, status = "Spotify 연결이 취소되었거나 실패했습니다.", 400
        body = f"""<!doctype html><html lang=\"ko\"><meta charset=\"utf-8\"><title>Spotify 연결</title>
        <body style=\"font-family:Arial,sans-serif;padding:48px;background:#111;color:#fff\">
        <h2>{message}</h2><p>이 창은 닫아도 됩니다.</p></body></html>"""
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *_: Any) -> None:
        pass


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge




def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _state_key(secret: str) -> bytes:
    value = str(secret or "").strip()
    if len(value) < 24:
        raise ValueError("OAuth state secret은 24자 이상이어야 합니다.")
    return value.encode("utf-8")


def build_web_authorization(client_id: str, redirect_uri: str, state_secret: str) -> dict[str, str]:
    """Create a stateless, signed Spotify PKCE request for Streamlit Cloud.

    Streamlit can establish a new browser session after an external OAuth redirect.
    The PKCE verifier is therefore carried inside an HMAC-signed state value instead
    of relying on ``st.session_state`` surviving the round trip.
    """
    verifier, challenge = _pkce_pair()
    payload = {
        "v": verifier,
        "n": secrets.token_urlsafe(16),
        "iat": int(time.time()),
        "cid": hashlib.sha256(client_id.encode("utf-8")).hexdigest()[:16],
        "uri": hashlib.sha256(redirect_uri.encode("utf-8")).hexdigest()[:16],
    }
    encoded = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _b64url_encode(hmac.new(_state_key(state_secret), encoded.encode("ascii"), hashlib.sha256).digest())
    state = f"{encoded}.{signature}"
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    return {"url": AUTH_URL + "?" + urllib.parse.urlencode(params), "state": state}


def verify_web_state(
    state: str, client_id: str, redirect_uri: str, state_secret: str, max_age_sec: int = 600
) -> str:
    """Validate a signed OAuth state and return its PKCE verifier."""
    try:
        encoded, supplied_signature = str(state).split(".", 1)
        expected_signature = _b64url_encode(
            hmac.new(_state_key(state_secret), encoded.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise ValueError("서명이 일치하지 않습니다.")
        payload = json.loads(_b64url_decode(encoded).decode("utf-8"))
        issued_at = int(payload.get("iat", 0))
        now = int(time.time())
        if issued_at <= 0 or now - issued_at > max_age_sec or issued_at > now + 60:
            raise ValueError("로그인 요청이 만료되었습니다.")
        expected_cid = hashlib.sha256(client_id.encode("utf-8")).hexdigest()[:16]
        expected_uri = hashlib.sha256(redirect_uri.encode("utf-8")).hexdigest()[:16]
        if payload.get("cid") != expected_cid or payload.get("uri") != expected_uri:
            raise ValueError("앱 정보가 일치하지 않습니다.")
        verifier = str(payload.get("v", ""))
        if len(verifier) < 43:
            raise ValueError("PKCE verifier가 올바르지 않습니다.")
        return verifier
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError(f"Spotify 로그인 state 검증 실패: {exc}") from exc


def exchange_web_code(client_id: str, redirect_uri: str, code: str, verifier: str) -> dict[str, Any]:
    """Exchange a hosted callback code for a Spotify token using PKCE."""
    response = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }, timeout=30)
    response.raise_for_status()
    token = response.json()
    token["saved_at"] = int(time.time())
    return token


def refresh_token_data(client_id: str, token: dict[str, Any]) -> dict[str, Any]:
    """Refresh an in-memory token without writing it to disk."""
    response = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": token["refresh_token"],
        "client_id": client_id,
    }, timeout=30)
    response.raise_for_status()
    refreshed = response.json()
    refreshed.setdefault("refresh_token", token["refresh_token"])
    refreshed["saved_at"] = int(time.time())
    return refreshed


def get_valid_token_data(client_id: str, token: dict[str, Any] | None) -> dict[str, Any] | None:
    """Validate or refresh a token stored in Streamlit session state."""
    if not token:
        return None
    expires_at = int(token.get("saved_at", 0)) + int(token.get("expires_in", 3600))
    if time.time() < expires_at - 60:
        return token
    if token.get("refresh_token"):
        try:
            return refresh_token_data(client_id, token)
        except requests.RequestException:
            return None
    return None


def save_token(token: dict[str, Any]) -> None:
    token["saved_at"] = int(time.time())
    TOKEN_FILE.write_text(json.dumps(token, ensure_ascii=False, indent=2), encoding="utf-8")


def load_token() -> dict[str, Any] | None:
    if not TOKEN_FILE.exists():
        return None
    try:
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def reset_token() -> None:
    TOKEN_FILE.unlink(missing_ok=True)


def refresh_token(client_id: str, token: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": token["refresh_token"],
        "client_id": client_id,
    }, timeout=30)
    response.raise_for_status()
    refreshed = response.json()
    refreshed.setdefault("refresh_token", token["refresh_token"])
    save_token(refreshed)
    return refreshed


def get_valid_token(client_id: str) -> dict[str, Any] | None:
    token = load_token()
    if not token:
        return None
    expires_at = int(token.get("saved_at", 0)) + int(token.get("expires_in", 3600))
    if time.time() < expires_at - 60:
        return token
    if token.get("refresh_token"):
        try:
            return refresh_token(client_id, token)
        except requests.RequestException:
            reset_token()
    return None


def authorize(client_id: str, timeout_sec: int = 180) -> dict[str, Any]:
    token = get_valid_token(client_id)
    if token:
        return token
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(24)
    _CallbackHandler.result = {}
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": LOCAL_REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    url = AUTH_URL + "?" + urllib.parse.urlencode(params)
    try:
        server = http.server.HTTPServer(("127.0.0.1", 8888), _CallbackHandler)
    except OSError as exc:
        raise RuntimeError("8888 포트를 사용할 수 없습니다. 다른 실행 창을 닫고 다시 시도하세요.") from exc
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    webbrowser.open(url)
    thread.join(timeout=timeout_sec)
    server.server_close()
    result = _CallbackHandler.result
    if not result:
        raise TimeoutError("3분 안에 Spotify 승인이 완료되지 않았습니다.")
    if result.get("error"):
        raise RuntimeError(f"Spotify 승인 실패: {result['error']}")
    if result.get("state") != state:
        raise RuntimeError("Spotify 로그인 state 검증에 실패했습니다.")
    response = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": result["code"],
        "redirect_uri": LOCAL_REDIRECT_URI,
        "code_verifier": verifier,
    }, timeout=30)
    response.raise_for_status()
    token = response.json()
    save_token(token)
    return token


class SpotifyAPI:
    def __init__(self, access_token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.session.request(method, API_BASE + path, timeout=30, **kwargs)
        if response.status_code == 429:
            time.sleep(int(response.headers.get("Retry-After", "2")))
            response = self.session.request(method, API_BASE + path, timeout=30, **kwargs)
        if response.status_code >= 500:
            time.sleep(1)
            response = self.session.request(method, API_BASE + path, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None

    def me(self) -> dict[str, Any]:
        return self.request("GET", "/me")

    def search_tracks(self, title: str, artist: str, limit: int = 10) -> list[dict[str, Any]]:
        queries = [f'track:"{title}" artist:"{artist.split(",")[0]}"', f"{title} {artist}"]
        found: dict[str, dict[str, Any]] = {}
        for query in queries:
            data = self.request("GET", "/search", params={"q": query, "type": "track", "limit": limit})
            items = data.get("tracks", {}).get("items", []) if isinstance(data, dict) else []
            for item in items:
                if item and item.get("id"):
                    found[item["id"]] = item
        return list(found.values())

    def search_discovery_tracks(self, query: str, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        data = self.request("GET", "/search", params={"q": query, "type": "track", "limit": min(limit, 10), "offset": offset})
        return data.get("tracks", {}).get("items", []) if isinstance(data, dict) else []

    def create_playlist(self, name: str, description: str, public: bool) -> dict[str, Any]:
        return self.request("POST", "/me/playlists", json={"name": name, "description": description, "public": public})

    def add_items(self, playlist_id: str, uris: list[str]) -> None:
        for start in range(0, len(uris), 100):
            self.request("POST", f"/playlists/{playlist_id}/items", json={"uris": uris[start:start + 100]})


def api_from_token(token: dict[str, Any]) -> SpotifyAPI:
    return SpotifyAPI(token["access_token"])


def candidate_score(title: str, artist: str, item: dict[str, Any]) -> float:
    wanted_title, got_title = normalize(title), normalize(item.get("name", ""))
    title_score = SequenceMatcher(None, wanted_title, got_title).ratio()
    wanted_artists = [normalize(x) for x in re.split(r",|&| feat\.? | featuring ", artist) if normalize(x)]
    got_artists = [normalize(x.get("name", "")) for x in item.get("artists", [])]
    if wanted_artists:
        artist_score = sum(max((SequenceMatcher(None, w, g).ratio() for g in got_artists), default=0) for w in wanted_artists) / len(wanted_artists)
    else:
        artist_score = 0.7
    score = 0.64 * title_score + 0.36 * artist_score
    if wanted_title == got_title:
        score += 0.05
    if wanted_artists and got_artists and wanted_artists[0] == got_artists[0]:
        score += 0.05
    return min(1.0, score)


def match_track(api: SpotifyAPI, title: str, artist: str) -> dict[str, Any]:
    candidates = api.search_tracks(title, artist)
    if not candidates:
        return {"include": False, "confidence": 0.0, "spotify_title": "", "spotify_artists": "", "spotify_uri": "", "spotify_url": "", "status": "검색 결과 없음"}
    # Compare candidates by numeric score only. Comparing (score, dict) tuples
    # raises TypeError when two candidates have exactly the same score.
    item = max(candidates, key=lambda candidate: candidate_score(title, artist, candidate))
    score = candidate_score(title, artist, item)
    artists = ", ".join(a.get("name", "") for a in item.get("artists", []))
    return {
        "include": score >= 0.78,
        "confidence": round(score, 3),
        "spotify_title": item.get("name", ""),
        "spotify_artists": artists,
        "spotify_uri": item.get("uri", ""),
        "spotify_url": item.get("external_urls", {}).get("spotify", ""),
        "status": "자동 매칭" if score >= 0.78 else "확인 필요",
    }


def match_set(api: SpotifyAPI, set_df: pd.DataFrame, progress: Callable[[int, int, str], None] | None = None) -> pd.DataFrame:
    rows = []
    total = len(set_df)
    for i, (_, row) in enumerate(set_df.iterrows(), 1):
        if progress:
            progress(i, total, f"{row['artist']} - {row['title']}")
        existing = str(row.get("spotify_uri", "") or "")
        if existing.startswith("spotify:track:"):
            matched = {"include": True, "confidence": 1.0, "spotify_title": row["title"], "spotify_artists": row["artist"], "spotify_uri": existing, "spotify_url": "", "status": "기존 URI"}
        else:
            matched = match_track(api, str(row["title"]), str(row["artist"]))
        rows.append({"order": int(row.get("order", i)), "input_title": row["title"], "input_artist": row["artist"], **matched})
    return pd.DataFrame(rows)


def _track_identity(item: dict[str, Any]) -> tuple[str, str]:
    title = normalize(item.get("name", ""))
    artist = normalize((item.get("artists") or [{}])[0].get("name", ""))
    return title, artist


def discover_fill_tracks(
    api: SpotifyAPI,
    set_df: pd.DataFrame,
    shortage_sec: int,
    genres: list[str],
    exclude_uris: set[str] | None = None,
) -> pd.DataFrame:
    """Find fill candidates using Spotify Search.

    The native Recommendations endpoint is unavailable to current Development Mode
    apps, so this uses genre filters and artists already present in the set as seeds.
    """
    exclude_uris = set(exclude_uris or set())
    existing_pairs = {
        (normalize(row.get("title", "")), normalize(row.get("artist", "")))
        for _, row in set_df.iterrows()
    }
    seed_artists = []
    for artist in set_df.get("artist", pd.Series(dtype=str)).fillna("").astype(str):
        primary = re.split(r",|&| feat\.? | featuring | x ", artist, flags=re.I)[0].strip()
        if primary and primary.casefold() not in {a.casefold() for a in seed_artists}:
            seed_artists.append(primary)
        if len(seed_artists) >= 8:
            break

    queries: list[tuple[str, str]] = []
    for genre in genres[:6]:
        queries.append((f'genre:"{genre}"', f"장르: {genre}"))
    for artist in seed_artists[:6]:
        queries.append((f'artist:"{artist}"', f"기존 아티스트: {artist}"))
    if not queries:
        queries = [(f'artist:"{artist}"', f"기존 아티스트: {artist}") for artist in seed_artists[:8]]
    if not queries:
        return pd.DataFrame(columns=["include", "title", "artist", "duration", "duration_sec", "source", "spotify_uri", "spotify_url"])

    pool: dict[str, dict[str, Any]] = {}
    for query, source in queries:
        for offset in (0, 10):
            try:
                items = api.search_discovery_tracks(query, limit=10, offset=offset)
            except requests.HTTPError:
                continue
            for item in items:
                uri = str(item.get("uri", ""))
                if not uri.startswith("spotify:track:") or uri in exclude_uris:
                    continue
                pair = _track_identity(item)
                if pair in existing_pairs:
                    continue
                duration_sec = max(0, int(item.get("duration_ms", 0) or 0) // 1000)
                if duration_sec <= 0:
                    continue
                if uri not in pool:
                    artists = ", ".join(a.get("name", "") for a in item.get("artists", []))
                    pool[uri] = {
                        "include": True,
                        "title": item.get("name", ""),
                        "artist": artists,
                        "duration": f"{duration_sec // 60}:{duration_sec % 60:02d}",
                        "duration_sec": duration_sec,
                        "source": source,
                        "spotify_uri": uri,
                        "spotify_url": item.get("external_urls", {}).get("spotify", ""),
                    }

    # Diversify artists while selecting enough duration to cover the shortage.
    candidates = list(pool.values())
    candidates.sort(key=lambda row: (row["source"].startswith("기존 아티스트"), row["artist"].casefold(), row["title"].casefold()))
    selected: list[dict[str, Any]] = []
    used_primary: set[str] = set()
    total = 0
    for pass_no in (0, 1):
        for row in candidates:
            if row in selected:
                continue
            primary = normalize(row["artist"].split(",")[0])
            if pass_no == 0 and primary in used_primary:
                continue
            selected.append(row)
            used_primary.add(primary)
            total += int(row["duration_sec"])
            if total >= shortage_sec + 120:
                break
        if total >= shortage_sec + 120:
            break
    return pd.DataFrame(selected)


def test_spotify_connection(client_id: str) -> tuple[bool, str]:
    """Validate the saved Spotify login and return a user-facing status."""
    client_id = client_id.strip()
    if not client_id:
        return False, "Client ID가 비어 있습니다."
    token = get_valid_token(client_id)
    if not token:
        return False, "저장된 Spotify 로그인이 없습니다. 먼저 연결을 승인하세요."
    try:
        user = api_from_token(token).me()
        name = user.get("display_name") or user.get("id") or "Spotify 사용자"
        return True, f"{name} 계정에 연결되었습니다."
    except requests.RequestException as exc:
        return False, f"Spotify 연결 확인 실패: {exc}"
