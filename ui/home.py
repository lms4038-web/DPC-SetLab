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
        ("01", "LIBRARY", "Rekordbox 후보곡"),
        ("02", "CONTEXT", "공연 상황 설정"),
        ("03", "BUILD", "AI 세트 생성"),
        ("04", "REFINE", "보충·재분석"),
        ("05", "PERFORM", "플랜 검토"),
    ]
    cards: list[str] = []
    for index, (num, name, desc) in enumerate(steps, start=1):
        active = " active" if index == active_step else ""
        cards.append(
            f'<div class="dpc-step{active}"><div class="num">STEP {num}</div>'
            f'<div class="name">{name}</div><div class="desc">{desc}</div></div>'
        )
    return '<div class="dpc-workflow">' + "".join(cards) + "</div>"


def detect_current_step(state: Any) -> int:
    if state.get("performance_plan") is not None:
        return 5
    if state.get("set_df") is not None:
        return 4
    if state.get("candidate_df") is not None:
        return 2
    if state.get("raw_collection") is not None:
        return 2
    return 1


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
          <div class="dpc-kicker">PROJECT ORCHESTRA · SPRINT 1A · PATCH 01</div>
          <div class="dpc-version">4.0.1-dev</div>
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
    spotify_sub = "플레이리스트 내보내기 준비됨" if spotify_connected else "사이드바에서 연결 필요"
    html = '<div class="dpc-card-grid">'
    html += _status_card("REKORDBOX LIBRARY", f"{library_count:,} TRACKS" if library_count else "EMPTY", "XML 또는 CSV 라이브러리")
    html += _status_card("ACTIVE CANDIDATES", f"{candidate_count:,} TRACKS" if candidate_count else "NOT SELECTED", "세트 생성에 사용할 후보")
    html += _status_card("CURRENT SET", f"{set_count:,} TRACKS" if set_count else "NOT BUILT", "마지막 AI 생성 결과", accent=bool(set_count))
    html += _status_card("SPOTIFY", spotify_value, spotify_sub)
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    st.markdown(
        '<div class="dpc-section-head"><h2>PERFORMANCE WORKFLOW</h2><span>보라색 단계가 현재 위치</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_workflow(active_step), unsafe_allow_html=True)

    left, right = st.columns([1.35, 1])
    with left:
        st.markdown("### Start a session")
        if library_count == 0:
            st.markdown(
                '<div class="dpc-empty"><b>첫 단계: 라이브러리 불러오기</b><br><br>'
                '상단의 <b>Library</b> 탭에서 Rekordbox XML 또는 CSV를 업로드하세요. '
                '샘플 데이터로 먼저 테스트할 수도 있습니다.</div>',
                unsafe_allow_html=True,
            )
        elif candidate_count == 0:
            st.info("라이브러리가 준비되었습니다. Library 탭에서 사용할 플레이리스트와 후보곡을 확정하세요.")
        elif set_count == 0:
            st.info("후보곡이 준비되었습니다. Set Builder 탭에서 공연 프리셋과 목표 시간을 정해 첫 세트를 생성하세요.")
        else:
            preset = st.session_state.get("build_preset_label", "Custom Session")
            st.success(f"현재 세트가 준비되었습니다 · {preset}")
            preview_columns = [c for c in ["order", "artist", "title", "bpm", "key", "energy"] if c in result.columns]
            if preview_columns:
                st.dataframe(result[preview_columns].head(6), use_container_width=True, hide_index=True)
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
            st.markdown("- 공통 디자인 시스템\n- 제품형 Home 화면\n- UI 모듈 분리\n- 기존 3.2 기능 및 OAuth 유지")
