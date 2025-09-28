from __future__ import annotations
import streamlit as st

# other admin imports here ...
from modules.utilities.reporting_fixed_panel import render_reporting_fixed_panel

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

    # ... render other admin sections in their indices ...

    # Utilities tab: Reporting Fixed lives here (only here)
    with tabs[6]:
        st.subheader("Utilities")
        try:
            render_reporting_fixed_panel()
        except Exception as e:
            st.error(f"Reporting Fixed panel failed: {e}")
