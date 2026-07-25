from __future__ import annotations

import streamlit as st


def render_spotify_oauth_link(
    url: str,
    *,
    label: str = "Spotify 연결",
    disabled: bool = False,
    key: str | None = None,
) -> None:
    """Render one Streamlit-native OAuth link across Home, onboarding and Settings."""
    st.link_button(
        label,
        url or "#",
        use_container_width=True,
        disabled=disabled or not bool(url),
        type="primary",
    )
