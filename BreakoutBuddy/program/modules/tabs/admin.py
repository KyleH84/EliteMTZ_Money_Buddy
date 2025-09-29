from __future__ import annotations
import streamlit as st
_panel = None
try:
    from modules.utilities.reporting_fixed_panel import render_reporting_fixed_panel as _panel  # type: ignore
except Exception:
    try:
        from ..utilities.reporting_fixed_panel import render_reporting_fixed_panel as _panel  # type: ignore
    except Exception:
        try:
            from ...pages.Reporting_Fixed import render_reporting_fixed_panel as _panel  # type: ignore
        except Exception:
            _panel = None

def render_admin() -> None:
    tabs = st.tabs([
        "Storage & Cache",
        "Agents & Rank",
        "Local LLMs",
        "Data QA",
        "Maintenance",
        "Market Regime",
        "Utilities",
    ])
    with tabs[6]:
        st.subheader("Utilities")
        if _panel is not None:
            try:
                _panel()
            except Exception as e:
                st.error(f"Reporting Fixed panel failed: {e}")
        else:
            st.info("Reporting Fixed panel module not found.")
