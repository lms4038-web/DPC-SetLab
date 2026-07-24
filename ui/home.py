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
        ("01", "LIBRARY", "Rekordbox 불러오기"),
        ("02", "CANDIDATES", "후보곡 확정·보강"),
        ("03", "PLANNER", "AI 생성·세트 검토"),
        ("04", "EXPORT", "Spotify 내보내기"),
    ]
    cards: list[str] = []
    for index, (num, name, desc) in enumerate(steps, start=1):
        active = " active" if index == active_step else ""
        cards.append(
            f'<div class="dpc-step{active}"><div class="num">STEP {num}</div>'
            f'<div class="name">{name}</div><div class="desc">{desc}</div></div>'
        )
    return '<div class="dpc-workflow dpc-workflow-four">' + "".join(cards) + "</div>"


def detect_current_step(state: Any) -> int:
    if state.get("spotify_export_complete"):
        return 4
    if state.get("set_df") is not None:
        return 4
    if state.get("candidate_df") is not None:
        return 3
    if state.get("raw_collection") is not None:
        return 2
    return 1


def _session_guide(active_step: int, spotify_connected: bool) -> tuple[str, str, str, list[tuple[str, bool]]]:
    guide = {
        1: ("LIBRARY", "Rekordbox XML 또는 CSV를 불러오세요.", "상단 LIBRARY 탭"),
        2: ("CANDIDATES", "공연에 사용할 후보곡을 확정하고 필요한 메타데이터를 보강하세요.", "상단 CANDIDATES 탭"),
        3: ("PLANNER", "공연 시간과 프리셋을 정하고 AI 세트를 생성한 뒤 결과를 검토하세요.", "상단 PLANNER 탭"),
        4: ("EXPORT", "완성된 세트를 Spotify 플레이리스트로 내보내세요.", "상단 EXPORT 탭"),
    }
    current, action, location = guide[active_step]
    checks = [
        ("라이브러리 불러오기", active_step > 1),
        ("후보곡 확정", active_step > 2),
        ("AI 세트 생성", active_step > 3),
        ("Spotify 연결", spotify_connected),
    ]
    return current, action, location, checks


def render_home(*, spotify_connected: bool, lastfm_configured: bool) -> None:
    collection = st.session_state.get("raw_collection")
    candidates = st.session_state.get("candidate_df")
    result = st.session_state.get("set_df")
    active_step = detect_current_step(st.session_state)

    library_count = len(collection) if isinstance(collection, pd.DataFrame) else 0
    candidate_count = len(candidates) if isinstance(candidates, pd.DataFrame) else 0
    set_count = len(result) if isinstance(result, pd.DataFrame) else 0

    st.markdown(
        """
        <div class="dpc-brandline">
          <div class="dpc-kicker">PROJECT ORCHESTRA · SPRINT 1A · PATCH 03</div>
          <div class="dpc-version">4.0.3-dev</div>
        </div>
        <section class="dpc-hero">
          <div class="dpc-kicker">DJ PERFORMANCE PLANNING SYSTEM</div>
          <h1>BUILD THE ARC.<br>CONTROL THE ROOM.</h1>
          <p>라이브러리를 불러오고, 공연의 에너지 곡선을 설계한 뒤, 실제 플레이 구간까지 하나의 흐름으로 준비합니다.</p>
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
    spotify_sub = "플레이리스트 내보내기 준비됨" if spotify_connected else "SETTINGS에서 연결 필요"
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
        current, next_action, next_location, checks = _session_guide(active_step, spotify_connected)
        progress = int(((active_step - 1) / 3) * 100)
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
        with st.expander("4.0 Sprint 1A 범위"):
            st.markdown("- 공통 디자인 시스템\n- 제품형 Home 및 Sidebar\n- 동적 Session Guide\n- 기존 3.2 기능 및 OAuth 유지")
