from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


WORKFLOW_STEPS = [
    ("Spotify", "계정 연결"),
    ("Rekordbox XML", "라이브러리 불러오기"),
    ("AI Set", "세트 생성"),
    ("Edit", "곡 순서와 믹스 검토"),
    ("Export", "Rekordbox·Spotify 내보내기"),
]


def detect_current_step(state: Any, spotify_connected: bool) -> int:
    """Return the first incomplete workflow step, 1 through 5."""
    if state.get("spotify_export_complete") or state.get("rekordbox_export_complete"):
        return 5
    if state.get("set_edit_complete"):
        return 5
    if isinstance(state.get("set_df"), pd.DataFrame):
        return 4
    if isinstance(state.get("raw_collection"), pd.DataFrame):
        return 3
    if spotify_connected:
        return 2
    return 1


def _workflow_statuses(*, spotify_connected: bool, xml_loaded: bool, set_ready: bool) -> list[bool]:
    edit_complete = bool(st.session_state.get("set_edit_complete"))
    export_complete = bool(
        st.session_state.get("spotify_export_complete")
        or st.session_state.get("rekordbox_export_complete")
    )
    return [spotify_connected, xml_loaded, set_ready, edit_complete, export_complete]


def _progress_html(statuses: list[bool], current_step: int) -> str:
    """Return compact HTML without Markdown indentation leaks."""
    rows: list[str] = []
    for index, ((label, description), complete) in enumerate(zip(WORKFLOW_STEPS, statuses), start=1):
        state_class = "done" if complete else ("current" if index == current_step else "pending")
        icon = "✓" if complete else (str(index) if index == current_step else "○")
        state_label = "완료" if complete else ("진행할 단계" if index == current_step else "대기")
        rows.append(
            f'<div class="dpc-home-progress-row {state_class}">'
            f'<div class="dpc-home-progress-icon">{icon}</div>'
            f'<div class="dpc-home-progress-copy"><b>{label}</b><span>{description}</span></div>'
            f'<div class="dpc-home-progress-state">{state_label}</div>'
            f'</div>'
        )
    return '<div class="dpc-home-progress">' + ''.join(rows) + '</div>'



def render_first_run_landing(*, spotify_connected: bool) -> None:
    """Render Patch 08's isolated first-run landing page.

    This page intentionally contains no dashboard, sidebar, tabs, analytics, or
    system tables. It exists only to explain the product and start onboarding.
    """
    status_label = "SPOTIFY CONNECTED" if spotify_connected else "READY TO START"
    status_class = "connected" if spotify_connected else "ready"
    st.markdown(
        f"""
        <main class="dpc-first-run">
          <div class="dpc-first-run-orbit orbit-one"></div>
          <div class="dpc-first-run-orbit orbit-two"></div>
          <div class="dpc-first-run-content">
            <div class="dpc-first-run-brand">DPC <span>SETLAB</span></div>
            <div class="dpc-first-run-kicker">AI DJ PERFORMANCE ASSISTANT</div>
            <h1>공연용 DJ 세트를<br><em>한 흐름으로 완성하세요.</em></h1>
            <p>Spotify 연결부터 Rekordbox XML, AI 세트 생성, 검토와 Export까지.<br>처음 사용하는 DJ도 순서대로 따라갈 수 있습니다.</p>
            <div class="dpc-first-run-status {status_class}"><i></i>{status_label}</div>
          </div>
        </main>
        <section class="dpc-first-run-flow">
          <div><b>01</b><span>Spotify</span><small>계정 연결</small></div>
          <div class="arrow">→</div>
          <div><b>02</b><span>Library</span><small>XML 업로드</small></div>
          <div class="arrow">→</div>
          <div><b>03</b><span>Generate</span><small>AI 세트 생성</small></div>
          <div class="arrow">→</div>
          <div><b>04</b><span>Edit</span><small>공연 전 검토</small></div>
          <div class="arrow">→</div>
          <div><b>05</b><span>Export</span><small>Rekordbox·Spotify</small></div>
        </section>
        """,
        unsafe_allow_html=True,
    )

def render_home(*, spotify_connected: bool, lastfm_configured: bool, xml_loaded: bool, set_ready: bool) -> None:
    """Render the contextual workspace home for Patch 08."""
    statuses = _workflow_statuses(
        spotify_connected=spotify_connected,
        xml_loaded=xml_loaded,
        set_ready=set_ready,
    )
    current_step = detect_current_step(st.session_state, spotify_connected)
    completed_count = sum(statuses)
    progress_percent = int(completed_count / len(statuses) * 100)

    st.markdown(
        """
        <section class="dpc-home-landing">
          <div class="dpc-home-eyebrow">PROJECT ORCHESTRA · PATCH 08</div>
          <div class="dpc-home-logo">🎧</div>
          <h1>DPC SetLab</h1>
          <h2>AI DJ Performance Assistant</h2>
          <p>Spotify 연결부터 Rekordbox XML, AI 세트 생성, 검토와 Export까지<br>공연 준비의 모든 단계를 하나의 흐름으로 완성하세요.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="dpc-home-overview-head">
          <div><span>현재 진행 상황</span><b>{completed_count} / 5 단계 완료</b></div>
          <strong>{progress_percent}%</strong>
        </div>
        <div class="dpc-home-progressbar"><span style="width:{progress_percent}%"></span></div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(_progress_html(statuses, current_step), unsafe_allow_html=True)

    button_label = "시작하기" if completed_count == 0 else "이어서 진행하기"
    if st.button(button_label, type="primary", use_container_width=True, key="home_start_wizard"):
        st.session_state["home_wizard_started"] = True

    if not st.session_state.get("home_wizard_started", False) and completed_count == 0:
        st.caption("처음 사용한다면 위 버튼을 눌러 Spotify 연결부터 순서대로 시작하세요.")
        return

    step_titles = {
        1: ("STEP 1", "Spotify를 연결하세요", "연결이 완료되면 다음 단계인 Rekordbox XML 업로드로 이동합니다."),
        2: ("STEP 2", "Rekordbox XML을 불러오세요", "LIBRARY 탭에서 XML 파일을 업로드하고 라이브러리 상태를 확인하세요."),
        3: ("STEP 3", "AI 세트를 생성하세요", "CANDIDATES에서 후보곡을 선택한 뒤 GENERATE에서 세트를 만드세요."),
        4: ("STEP 4", "공연 전 세트를 검토하세요", "EDIT에서 곡 순서, BPM, Key와 실제 믹스 구간을 확인하세요."),
        5: ("STEP 5", "Rekordbox와 Spotify로 내보내세요", "EXPORT에서 업데이트된 XML과 필요한 파일을 생성하세요."),
    }
    step_no, title, body = step_titles[current_step]
    st.markdown(
        f"""
        <div class="dpc-home-next-card">
          <div class="dpc-home-next-step">{step_no}</div>
          <div><h3>{title}</h3><p>{body}</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if current_step > 1:
        c1, c2, c3 = st.columns(3)
        collection = st.session_state.get("raw_collection")
        result = st.session_state.get("set_df")
        library_count = len(collection) if isinstance(collection, pd.DataFrame) else 0
        set_count = len(result) if isinstance(result, pd.DataFrame) else 0
        c1.metric("Rekordbox Library", f"{library_count:,}곡")
        c2.metric("Current Set", f"{set_count:,}곡")
        c3.metric("System", "READY" if lastfm_configured else "READY · Last.fm 선택")

    with st.expander("전체 Quick Start 흐름 보기"):
        st.markdown(
            """
            **1. Spotify 연결** → **2. Rekordbox XML 업로드** → **3. AI 세트 생성**  
            → **4. Edit에서 공연 전 검토** → **5. Rekordbox XML·Spotify Export**
            """
        )
