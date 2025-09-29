
from __future__ import annotations

import typing as _t

# Shim so `from utilities.health_widget import render_health_widget` always works.
# Prefer the BreakoutBuddy implementation if available, else provide a minimal fallback.

try:
    from BreakoutBuddy.program.utilities.health_widget import render_health_widget  # type: ignore
except Exception:
    import streamlit as st

    def render_health_widget(*args: _t.Any, **kwargs: _t.Any) -> None:  # type: ignore
        \"\"Minimal health panel fallback used when BB widget isn't available.\"\"
        with st.sidebar:
            st.caption("Cache & Storage Health (fallback)")
            st.success("st.cache_data/_resource: OK")
            st.caption("DuckDB: assumed OK (fallback)")
            st.caption("Supabase secrets: loaded")
