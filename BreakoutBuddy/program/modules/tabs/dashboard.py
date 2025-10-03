from __future__ import annotations

import streamlit as st
import pandas as pd

from BreakoutBuddy.program.modules.data import list_universe, pull_enriched_snapshot
from BreakoutBuddy.program.modules.services.enrich import ensure_features
from BreakoutBuddy.program.modules.explain import explain_scan

def render_dashboard_tab():
    st.subheader("BreakoutBuddy • Dashboard")
    n = int(st.session_state.get("universe_size", 500))
    topn = int(st.session_state.get("rows_to_display", 25))

    if st.button("Refresh now (fetch & rank)"):
        st.session_state["_bb_force_refresh"] = True

    try:
        syms = list_universe(n=n)
    except TypeError:
        syms = list_universe(n)

    df = pull_enriched_snapshot(syms)
    if df is None or df.empty:
        st.info("No snapshot available yet. Try **Refresh now**.")
        return

    # Ensure required features exist numerically
    df = ensure_features(df)

    # Quick explain (pros/cons badge) for display
    try:
        add = explain_scan(df.head(topn))
        # align back to df
        for col in ("QuickWhy","RiskBadge"):
            if col in add.columns:
                df[col] = add[col]
    except Exception:
        pass

    st.caption(f"Showing top N from Controls: {topn}")
    st.dataframe(df.head(topn), use_container_width=True)
