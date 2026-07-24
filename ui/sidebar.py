from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


def _count_df(value: Any) -> int:
    return len(value) if isinstance(value, pd.DataFrame) else 0


def render_sidebar_header() -> None:
    st.markdown(
        """
        <div class="dpc-side-brand">
          <div class="dpc-side-logo">◉</div>
          <div>
            <div class="dpc-side-title">DPC SETLAB <span>4.0</span></div>
            <div class="dpc-side-subtitle">PROJECT ORCHESTRA</div>
          </div>
        </div>
        <div class="dpc-side-profile-label">DJ PROFILE</div>
        <div class="dpc-side-profile">
          <div class="dpc-avatar">DPC</div>
          <div>
            <div class="dpc-profile-name">DJ Purple Cigarette</div>
            <div class="dpc-profile-role">DJ / Producer</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_session_snapshot() -> None:
    library_count = _count_df(st.session_state.get("raw_collection"))
    candidate_count = _count_df(st.session_state.get("candidate_df"))
    set_count = _count_df(st.session_state.get("set_df"))

    st.markdown('<div class="dpc-side-section-title">SESSION SNAPSHOT</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="dpc-side-snapshot">
          <div><span>LIBRARY</span><b>{library_count:,}</b></div>
          <div><span>CANDIDATES</span><b>{candidate_count:,}</b></div>
          <div><span>CURRENT SET</span><b>{set_count:,}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_footer() -> None:
    st.markdown(
        """
        <div class="dpc-side-footer">
          <span class="dpc-live-dot"></span>
          <span>ORCHESTRA ENGINE READY</span>
        </div>
        """,
        unsafe_allow_html=True,
    )



def _spotify_track_id(uri_or_url: str) -> str:
    value = str(uri_or_url or "").strip()
    if value.startswith("spotify:track:"):
        return value.rsplit(":", 1)[-1]
    if "open.spotify.com/track/" in value:
        return value.split("open.spotify.com/track/", 1)[-1].split("?", 1)[0].split("/", 1)[0]
    return ""


def _spotify_playlist_id(uri_or_url: str) -> str:
    value = str(uri_or_url or "").strip()
    if value.startswith("spotify:playlist:"):
        return value.rsplit(":", 1)[-1]
    if "open.spotify.com/playlist/" in value:
        return value.split("open.spotify.com/playlist/", 1)[-1].split("?", 1)[0].split("/", 1)[0]
    return ""


def _render_spotify_embed(kind: str, spotify_id: str, height: int) -> None:
    if not spotify_id:
        return
    src = f"https://open.spotify.com/embed/{kind}/{spotify_id}?utm_source=generator&theme=0"
    html = (
        f'<iframe style="border-radius:12px" src="{src}" width="100%" height="{height}" '
        'frameborder="0" allowfullscreen="" '
        'allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" '
        'loading="lazy"></iframe>'
    )
    components.html(html, height=height + 8)


def render_set_player() -> None:
    """Render a compact Spotify player for the current set."""
    set_df = st.session_state.get("set_df")
    if not isinstance(set_df, pd.DataFrame) or set_df.empty:
        return

    st.markdown('<div class="dpc-side-section-title">SET PLAYER</div>', unsafe_allow_html=True)
    playlist_url = str(st.session_state.get("spotify_playlist_url", "") or "")
    playlist_id = _spotify_playlist_id(playlist_url)
    if playlist_id:
        playlist_name = str(st.session_state.get("spotify_playlist_name", "현재 세트") or "현재 세트")
        st.caption(f"{playlist_name} · Spotify playlist")
        _render_spotify_embed("playlist", playlist_id, 352)
        return

    matches = st.session_state.get("spotify_matches")
    if not isinstance(matches, pd.DataFrame) or matches.empty or "spotify_uri" not in matches.columns:
        st.caption("EXPORT에서 Spotify 곡 매칭을 하면 이곳에서 세트 곡을 바로 들어볼 수 있습니다.")
        return

    playable = matches[matches["spotify_uri"].astype(str).str.startswith("spotify:track:")].copy()
    if "include" in playable.columns:
        playable = playable[playable["include"].fillna(False)]
    if playable.empty:
        st.caption("재생 가능한 Spotify 매칭 곡이 없습니다.")
        return

    labels = []
    rows = []
    for index, row in playable.reset_index(drop=True).iterrows():
        title = str(row.get("spotify_title") or row.get("input_title") or "Unknown track")
        artist = str(row.get("spotify_artists") or row.get("input_artist") or "Unknown artist")
        order = row.get("order", index + 1)
        try:
            order_text = f"{int(order):02d}"
        except Exception:
            order_text = f"{index + 1:02d}"
        labels.append(f"{order_text}. {artist} – {title}")
        rows.append(row)

    selected = st.selectbox(
        "현재 세트 곡",
        range(len(rows)),
        format_func=lambda i: labels[i],
        key="sidebar_set_player_track",
        label_visibility="collapsed",
    )
    track_id = _spotify_track_id(str(rows[selected].get("spotify_uri", "")))
    _render_spotify_embed("track", track_id, 152)
    st.caption("플레이리스트를 생성하면 전체 세트를 순서대로 재생할 수 있습니다.")
