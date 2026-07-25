from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


WORKFLOW_STEPS = [
    ("Spotify", "계정 연결"),
    ("Library", "Rekordbox XML 불러오기"),
    ("Candidates", "후보곡 선택"),
    ("Generate", "AI 세트 생성"),
    ("Edit", "공연 전 검토"),
    ("Export", "Rekordbox·Spotify 내보내기"),
]


def detect_current_step(state: Any, spotify_connected: bool) -> int:
    """Return the first incomplete workflow step, 1 through 6."""
    export_complete = bool(
        state.get("spotify_export_complete")
        or state.get("rekordbox_export_complete")
    )
    if export_complete:
        return 6
    if state.get("set_edit_complete"):
        return 6
    if isinstance(state.get("set_df"), pd.DataFrame):
        return 5 if state.get("generate_review_complete") else 4
    if isinstance(state.get("candidate_df"), pd.DataFrame):
        return 4
    if isinstance(state.get("raw_collection"), pd.DataFrame):
        return 3
    if spotify_connected:
        return 2
    return 1


def workflow_statuses(*, spotify_connected: bool) -> list[bool]:
    state = st.session_state
    return [
        spotify_connected,
        isinstance(state.get("raw_collection"), pd.DataFrame),
        isinstance(state.get("candidate_df"), pd.DataFrame),
        bool(state.get("generate_review_complete")),
        bool(state.get("set_edit_complete")),
        bool(state.get("spotify_export_complete") or state.get("rekordbox_export_complete")),
    ]


def _compact_progress_html(statuses: list[bool], current_step: int) -> str:
    items: list[str] = []
    for index, ((label, _), complete) in enumerate(zip(WORKFLOW_STEPS, statuses), start=1):
        css = "done" if complete else ("current" if index == current_step else "pending")
        mark = "✓" if complete else str(index)
        items.append(
            f'<div class="dpc-wizard-step {css}"><span>{mark}</span><b>{label}</b></div>'
        )
    return '<div class="dpc-wizard-progress">' + ''.join(items) + '</div>'


def render_first_run_landing(*, spotify_connected: bool) -> None:
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
            <h1>더 좋은 DJ 세트를<br><em>AI와 함께 완성하세요.</em></h1>
            <p>Spotify와 Rekordbox 라이브러리를 연결하고,<br>AI가 후보곡 분석부터 세트 생성과 Export까지 도와드립니다.</p>
            <div class="dpc-first-run-status {status_class}"><i></i>{status_label}</div>
          </div>
        </main>
        <section class="dpc-first-run-flow">
          <div><b>01</b><span>Spotify</span><small>계정 연결</small></div>
          <div><b>02</b><span>Library</span><small>XML 업로드</small></div>
          <div><b>03</b><span>Candidates</span><small>후보곡 선택</small></div>
          <div><b>04</b><span>Generate</span><small>AI 세트 생성</small></div>
          <div><b>05</b><span>Edit</span><small>공연 전 검토</small></div>
          <div><b>06</b><span>Export</span><small>Rekordbox·Spotify</small></div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_home(*, spotify_connected: bool) -> str | None:
    """Render the v5.0 wizard home and return the requested next tab key."""
    statuses = workflow_statuses(spotify_connected=spotify_connected)
    current_step = detect_current_step(st.session_state, spotify_connected)

    st.markdown(
        """
        <section class="dpc-home-landing dpc-home-landing-compact">
          <div class="dpc-home-eyebrow">DPC SETLAB 5.0 · AI DJ PERFORMANCE ASSISTANT</div>
          <h1>공연용 세트를 준비하세요.</h1>
          <p>현재 단계만 완료하면 다음 작업으로 바로 이어집니다.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(_compact_progress_html(statuses, current_step), unsafe_allow_html=True)

    step_content = {
        1: ("STEP 1", "Spotify를 연결하세요.", "음악 검색과 Spotify Export에 사용됩니다.", "Spotify 연결", None),
        2: ("STEP 2", "Rekordbox XML을 불러오세요.", "Library에서 rekordbox.xml을 업로드하세요.", "LIBRARY 열기", "library"),
        3: ("STEP 3", "후보곡을 선택하세요.", "AI가 세트를 만들 때 사용할 곡을 정합니다.", "CANDIDATES 열기", "candidates"),
        4: ("STEP 4", "AI 믹스셋을 생성하고 검토하세요.", "생성 결과와 전환 정보를 확인한 뒤 Edit으로 이동합니다.", "GENERATE 열기", "generate"),
        5: ("STEP 5", "세트를 검토하세요.", "곡 순서와 믹스 구간을 확인하고 저장하세요.", "EDIT 열기", "edit"),
        6: ("STEP 6", "세트를 내보내세요.", "Rekordbox XML 또는 Spotify Playlist로 완성합니다.", "EXPORT 열기", "export"),
    }
    step_no, title, body, button_label, target = step_content[current_step]
    st.markdown(
        f"""
        <section class="dpc-wizard-card">
          <div class="dpc-wizard-card-step">{step_no}</div>
          <h2>{title}</h2>
          <p>{body}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if target and st.button(button_label, type="primary", use_container_width=True, key=f"home_next_{target}"):
        return target

    if current_step == 1:
        st.caption("아래 Spotify 연결 버튼을 사용해 STEP 1을 완료하세요.")
    elif statuses[-1]:
        st.success("세트 Export가 완료되었습니다. 상단 탭에서 언제든 이전 단계를 다시 확인할 수 있습니다.")
    return None
