from __future__ import annotations

from pathlib import Path

import streamlit as st

STYLE_FILES = (
    "theme.css",
    "base.css",
    "components.css",
    "desktop.css",
    "tablet.css",
    "mobile.css",
    "safari.css",
)


def load_external_theme() -> None:
    """Load the split DPC SetLab stylesheet bundle in deterministic order."""
    style_dir = Path(__file__).resolve().parent.parent / "styles"
    chunks: list[str] = []
    for filename in STYLE_FILES:
        path = style_dir / filename
        if path.exists():
            chunks.append(f"/* {filename} */\n{path.read_text(encoding='utf-8')}")
    if chunks:
        st.markdown("<style>\n" + "\n".join(chunks) + "\n</style>", unsafe_allow_html=True)
