from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


"""
Sidebar utilities for AstroLotto (cleaned version handling).
"""

import logging

try:
    import streamlit as st
except Exception:
    st = None

logger = logging.getLogger(__name__)

def get_version() -> str:
    """
    Legacy helper: try to read extras/version.txt if it exists.
    Only used as a fallback if app_version is not provided.
    """
    try:
        with open("extras/version.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "Unknown"

def render_version_badge(prefix: str = "Version", app_version: str | None = None) -> None:
    """
    Render a small caption in the sidebar with the version string.

    If Streamlit is not available, this function does nothing.
    If `app_version` is provided, it takes precedence over version.txt.
    """
    if st is None:
        return
    version = app_version or get_version()
    st.sidebar.caption(f"{prefix}: {version}")

def render_experimental_sidebar() -> dict:
    """
    Example stub for future flags; extend as needed.
    """
    if st is None:
        return {}
    st.sidebar.header("Experimental Features")
    opts = {}
    # You can add new sidebar options here if needed
    return opts
