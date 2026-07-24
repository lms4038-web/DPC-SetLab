from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


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
