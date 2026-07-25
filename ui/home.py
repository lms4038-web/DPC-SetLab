from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def _status_card(label: str, value: str, sub: str, accent: bool = False) -> str:
    klass = "value dpc-accent" if accent else "value"
    return (
        '<div class="dpc-card">'
        f'<div class="label">{label}</div>'
        f'<div class="{klass}">{value}</div>'
        f'<div class="sub">{sub}</div>'
        '</div>'
    )


def _workflow(active_step: int) -> str:
    steps = [
        ("01", "SPOTIFY", "계정 연결"),
        ("02", "LIBRARY", "Rekordbox XML"),
        ("03", "GENERATE", "AI 세트 생성"),
        ("04", "EDIT", "공연 전 검토"),
        ("05", "EXPORT", "Rekordbox·Spotify"),
    ]
    cards: list[str] = []
    for index, (num, name, desc) in enumerate(steps, start=1):
        active = " active" if index == active_step else ""
        cards.append(
            f'<div class="dpc-step{active}"><div class="num">STEP {num}</div>'
            f'<div class="name">{name}</div><div class="desc">{desc}</div></div>'
        )
    return '<div class="dpc-workflow dpc-workflow-five">' + "".join(cards) + "</div>"


def detect_current_step(state: Any, spotify_connected: bool) -> int:
    if state.get("spotify_export_complete") or state.get("rekordbox_export_complete"):
        return 5
    if state.get("set_edit_complete"):
        return 5
    if state.get("set_df") is not None:
        return 4
    if state.get("raw_collection") is not None:
        return 3
    if spotify_connected:
        return 2
    return 1


def _session_guide(active_step: int) -> tuple[str, str, str, list[tuple[str, bool]]]:
    guide = {
        1: ("SPOTIFY", "Spotify를 연결하세요.", "HOME 아래 연결 영역"),
        2: ("LIBRARY", "Rekordbox XML을 업로드하세요.", "상단 LIBRARY 탭"),
        3: ("GENERATE", "후보곡을 확인하고 AI 세트를 생성하세요.", "CANDIDATES와 GENERATE 탭"),
        4: ("EDIT", "곡 순서와 실제 믹스 구간을 검토하세요.", "상단 EDIT 탭"),
        5: ("EXPORT", "Rekordbox XML과 Spotify Playlist로 내보내세요.", "상단 EXPORT 탭"),
    }
    current, action, location = guide[active_step]
    checks = [
        ("Spotify 연결", active_step > 1),
        ("XML 불러오기", active_step > 2),
        ("AI 세트 생성", active_step > 3),
        ("세트 검토", active_step > 4),
    ]
    return current, action, location, checks

def render_home(*, spotify_connected: bool, lastfm_configured: bool, xml_loaded: bool, set_ready: bool) -> None:
    collection = st.session_state.get("raw_collection")
    candidates = st.session_state.get("candidate_df")
    result = st.session_state.get("set_df")
    active_step = detect_current_step(st.session_state, spotify_connected)

    library_count = len(collection) if isinstance(collection, pd.DataFrame) else 0
    candidate_count = len(candidates) if isinstance(candidates, pd.DataFrame) else 0
    set_count = len(result) if isinstance(result, pd.DataFrame) else 0

    st.markdown(
        """
        <div class="dpc-brandline">
          <div class="dpc-kicker">PROJECT ORCHESTRA · SPRINT 2 · PATCH 07</div>
          <div class="dpc-version">4.0.7-dev</div>
        </div>
        <section class="dpc-hero">
          <div class="dpc-kicker">DJ PERFORMANCE PLANNING SYSTEM</div>
          <h1>CONNECT. BUILD.<br>PERFORM.</h1>
          <p>Spotify 연결부터 Rekordbox XML, AI 생성, 검토, Export까지 처음 사용하는 DJ도 한 흐름으로 완성합니다.</p>
          <div class="dpc-live-chip"><span class="dpc-live-dot"></span>ORCHESTRA ENGINE ONLINE</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="dpc-section-head"><h2>SESSION STATUS</h2><span>현재 작업 상태</span></div>',
        unsafe_allow_html=True,
    )
    spotify_value = "CONNECTED" if spotify_connected else "NOT CONNECTED"
    spotify_sub = "첫 단계 완료" if spotify_connected else "HOME에서 먼저 연결"
    html = '<div class="dpc-card-grid">'
    html += _status_card("REKORDBOX LIBRARY", f"{library_count:,} TRACKS" if library_count else "EMPTY", "XML 또는 CSV 라이브러리")
    html += _status_card("ACTIVE CANDIDATES", f"{candidate_count:,} TRACKS" if candidate_count else "NOT SELECTED", "세트 생성에 사용할 후보")
    html += _status_card("CURRENT SET", f"{set_count:,} TRACKS" if set_count else "NOT BUILT", "마지막 AI 생성 결과", accent=bool(set_count))
    html += _status_card("SPOTIFY", spotify_value, spotify_sub)
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    st.markdown(
        '<div class="dpc-section-head"><h2>SESSION WORKFLOW</h2><span>상단 핵심 메뉴와 같은 이름으로 진행됩니다</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_workflow(active_step), unsafe_allow_html=True)

    left, right = st.columns([1.35, 1])
    with left:
        current, next_action, next_location, checks = _session_guide(active_step)
        progress = int(((active_step - 1) / 4) * 100)
        checklist_html = "".join(
            f'<div class="dpc-guide-check {"done" if done else "pending"}"><span>{"✓" if done else "○"}</span>{label}</div>'
            for label, done in checks
        )
        guide_html = f"""
        <div class="dpc-guide">
          <div class="dpc-guide-top">
            <div><div class="dpc-kicker">SESSION GUIDE</div><h3>현재 단계 · {current}</h3></div>
            <div class="dpc-guide-percent">{progress}%</div>
          </div>
          <div class="dpc-progress"><span style="width:{progress}%"></span></div>
          <div class="dpc-guide-action">
            <div class="label">NEXT ACTION</div>
            <b>{next_action}</b>
            <p>{next_location}에서 계속할 수 있습니다.</p>
          </div>
          <div class="dpc-guide-checks">{checklist_html}</div>
        </div>
        """
        st.markdown(guide_html, unsafe_allow_html=True)
        if set_count and isinstance(result, pd.DataFrame):
            preview_columns = [c for c in ["order", "artist", "title", "bpm", "key", "energy"] if c in result.columns]
            if preview_columns:
                with st.expander(f"현재 세트 전체 보기 · {set_count}곡", expanded=False):
                    preview_height = min(560, max(220, 38 * (set_count + 1)))
                    st.dataframe(
                        result[preview_columns],
                        use_container_width=True,
                        hide_index=True,
                        height=preview_height,
                    )
    with right:
        st.markdown("### System check")
        checks = pd.DataFrame(
            [
                {"Module": "Spotify", "Status": "Ready" if spotify_connected else "Setup required"},
                {"Module": "Last.fm", "Status": "Ready" if lastfm_configured else "Optional"},
                {"Module": "Structure Engine", "Status": "Online"},
                {"Module": "Performance Planner", "Status": "Online"},
            ]
        )
        st.dataframe(checks, use_container_width=True, hide_index=True)
        with st.expander("4.0.7 Patch 07 범위"):
            st.markdown("- Spotify-first 온보딩\n- 5단계 Quick Start\n- Library XML Guide\n- Generate / Edit 분리\n- Export 이후 Rekordbox 안내")
