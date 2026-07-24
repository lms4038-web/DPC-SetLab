from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

import pandas as pd
import requests

CACHE_FILE = Path("online_metadata_cache.json")
USER_AGENT = "DPC-SetLab/2.1 (local DJ tool)"


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip()).casefold()


def _cache_key(artist: str, title: str) -> str:
    raw = f"{_norm(artist)}|{_norm(title)}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def load_cache() -> dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(cache: dict[str, Any]) -> None:
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_json(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 12) -> dict[str, Any]:
    merged = {"User-Agent": USER_AGENT}
    if headers:
        merged.update(headers)
    response = requests.get(url, params=params, headers=merged, timeout=timeout)
    response.raise_for_status()
    return response.json()


def musicbrainz_lookup(artist: str, title: str) -> dict[str, Any]:
    query = f'recording:"{title}" AND artist:"{artist}"'
    data = _get_json(
        "https://musicbrainz.org/ws/2/recording/",
        params={"query": query, "fmt": "json", "limit": 5},
    )
    recordings = data.get("recordings", [])
    if not recordings:
        return {}
    best = recordings[0]
    releases = best.get("releases", []) or []
    years = []
    countries = []
    labels = []
    for rel in releases[:5]:
        date = str(rel.get("date", ""))
        if date[:4].isdigit():
            years.append(int(date[:4]))
        if rel.get("country"):
            countries.append(str(rel["country"]))
        for info in rel.get("label-info", []) or []:
            label = (info.get("label") or {}).get("name")
            if label:
                labels.append(str(label))
    tags = [t.get("name", "") for t in best.get("tags", []) if t.get("name")]
    credits = [c.get("name", "") for c in best.get("artist-credit", []) if isinstance(c, dict) and c.get("name")]
    return {
        "musicbrainz_id": best.get("id", ""),
        "release_year": min(years) if years else None,
        "countries": sorted(set(countries))[:5],
        "labels": sorted(set(labels))[:5],
        "mb_tags": tags[:10],
        "credited_artists": credits,
        "mb_score": best.get("score"),
    }


def lastfm_lookup(artist: str, title: str, api_key: str) -> dict[str, Any]:
    if not api_key:
        return {}
    data = _get_json(
        "https://ws.audioscrobbler.com/2.0/",
        params={
            "method": "track.getInfo", "api_key": api_key,
            "artist": artist, "track": title, "autocorrect": 1, "format": "json",
        },
    )
    track = data.get("track") or {}
    tags = [t.get("name", "") for t in (track.get("toptags") or {}).get("tag", []) if t.get("name")]
    similar = []
    for t in (track.get("similar") or {}).get("track", [])[:8]:
        a = (t.get("artist") or {}).get("name", "")
        if a:
            similar.append(a)
    album = track.get("album") or {}
    return {
        "lastfm_tags": tags[:10],
        "lastfm_listeners": int(track.get("listeners", 0) or 0),
        "lastfm_playcount": int(track.get("playcount", 0) or 0),
        "similar_artists": sorted(set(similar)),
        "lastfm_album": album.get("title", ""),
        "lastfm_url": track.get("url", ""),
    }


def discogs_lookup(artist: str, title: str, token: str) -> dict[str, Any]:
    if not token:
        return {}
    data = _get_json(
        "https://api.discogs.com/database/search",
        params={"artist": artist, "track": title, "type": "release", "per_page": 5, "token": token},
    )
    results = data.get("results", [])
    if not results:
        # Discogs track filtering can be sparse; retry with a general query.
        data = _get_json(
            "https://api.discogs.com/database/search",
            params={"q": f"{artist} {title}", "type": "release", "per_page": 5, "token": token},
        )
        results = data.get("results", [])
    if not results:
        return {}
    best = results[0]
    return {
        "discogs_year": best.get("year") or None,
        "discogs_genres": best.get("genre", []) or [],
        "discogs_styles": best.get("style", []) or [],
        "discogs_labels": best.get("label", []) or [],
        "discogs_country": best.get("country", ""),
        "discogs_url": f"https://www.discogs.com{best.get('uri', '')}" if best.get("uri") else "",
    }


def spotify_lookup(artist: str, title: str, api: Any | None) -> dict[str, Any]:
    if api is None:
        return {}
    try:
        query = f'track:"{title}" artist:"{artist}"'
        data = api.get("/search", params={"q": query, "type": "track", "limit": 5})
        items = ((data.get("tracks") or {}).get("items") or [])
        if not items:
            return {}
        best = items[0]
        album = best.get("album") or {}
        return {
            "spotify_id": best.get("id", ""),
            "spotify_popularity": int(best.get("popularity", 0) or 0),
            "spotify_release_date": album.get("release_date", ""),
            "spotify_album": album.get("name", ""),
            "spotify_url": ((best.get("external_urls") or {}).get("spotify", "")),
        }
    except Exception:
        return {}


def merge_tags(meta: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("lastfm_tags", "mb_tags", "discogs_genres", "discogs_styles"):
        for item in meta.get(key, []) or []:
            value = str(item).strip()
            if value and _norm(value) not in {_norm(v) for v in values}:
                values.append(value)
    return values[:12]


def enrich_track(
    artist: str,
    title: str,
    *,
    lastfm_api_key: str = "",
    discogs_token: str = "",
    spotify_api: Any | None = None,
    use_musicbrainz: bool = True,
    use_lastfm: bool = True,
    use_discogs: bool = False,
    use_spotify: bool = True,
    force_refresh: bool = False,
) -> dict[str, Any]:
    cache = load_cache()
    key = _cache_key(artist, title)
    if not force_refresh and key in cache:
        return cache[key]

    meta: dict[str, Any] = {"online_status": "ok", "online_errors": []}
    sources: list[str] = []
    lookups: list[tuple[str, Callable[[], dict[str, Any]]]] = []
    if use_musicbrainz:
        lookups.append(("MusicBrainz", lambda: musicbrainz_lookup(artist, title)))
    if use_lastfm and lastfm_api_key:
        lookups.append(("Last.fm", lambda: lastfm_lookup(artist, title, lastfm_api_key)))
    if use_spotify and spotify_api is not None:
        lookups.append(("Spotify", lambda: spotify_lookup(artist, title, spotify_api)))
    if use_discogs and discogs_token:
        lookups.append(("Discogs", lambda: discogs_lookup(artist, title, discogs_token)))

    for source, fn in lookups:
        try:
            result = fn()
            if result:
                meta.update(result)
                sources.append(source)
        except Exception as exc:
            meta["online_errors"].append(f"{source}: {exc}")
        if source == "MusicBrainz":
            time.sleep(1.05)  # Respect MusicBrainz public-service rate guidance.

    meta["online_sources"] = sources
    meta["online_tags"] = merge_tags(meta)
    if not sources:
        meta["online_status"] = "not_found"
    elif meta["online_errors"]:
        meta["online_status"] = "partial"

    cache[key] = meta
    save_cache(cache)
    return meta


def enrich_dataframe(
    df: pd.DataFrame,
    *,
    lastfm_api_key: str = "",
    discogs_token: str = "",
    spotify_api: Any | None = None,
    use_musicbrainz: bool = True,
    use_lastfm: bool = True,
    use_discogs: bool = False,
    use_spotify: bool = True,
    force_refresh: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> pd.DataFrame:
    out = df.copy()
    records = []
    total = len(out)
    for pos, (_, row) in enumerate(out.iterrows(), start=1):
        label = f"{row.get('artist', '')} – {row.get('title', '')}"
        if progress_callback:
            progress_callback(pos, total, label)
        meta = enrich_track(
            str(row.get("artist", "")), str(row.get("title", "")),
            lastfm_api_key=lastfm_api_key, discogs_token=discogs_token, spotify_api=spotify_api,
            use_musicbrainz=use_musicbrainz, use_lastfm=use_lastfm,
            use_discogs=use_discogs, use_spotify=use_spotify, force_refresh=force_refresh,
        )
        records.append(meta)

    meta_df = pd.DataFrame(records, index=out.index)
    for col in meta_df.columns:
        out[col] = meta_df[col]
    out["online_tags_text"] = out.get("online_tags", pd.Series([[]] * len(out), index=out.index)).apply(
        lambda v: ", ".join(v) if isinstance(v, list) else str(v or "")
    )
    out["online_sources_text"] = out.get("online_sources", pd.Series([[]] * len(out), index=out.index)).apply(
        lambda v: ", ".join(v) if isinstance(v, list) else str(v or "")
    )
    return out
