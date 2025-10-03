from __future__ import annotations

import streamlit as st
import pandas as pd

# Data/services
from BreakoutBuddy.program.modules.data import list_universe, pull_enriched_snapshot

# Optional: if an external feature gap filler exists, use it (no hard dependency)
try:
    from utilities.feature_fixups import fill_feature_gaps  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.feature_fixups import ensure_basic_indicators as fill_feature_gaps  # type: ignore
    except Exception:
        def fill_feature_gaps(df: pd.DataFrame, spy_ref=None) -> pd.DataFrame:  # type: ignore
            return df

def _ensure_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    need = ["P_up","ConnorsRSI","SqueezeHint","AgentBoost_exact"]
    for c in need:
        if c not in df.columns:
            df[c] = None
    df["AgentBoost_exact"] = df["AgentBoost_exact"].fillna(0)
    for c in ["P_up","ConnorsRSI","SqueezeHint"]:
        if c in df.columns:
            df[c] = df[c].fillna("None")
    return df

def _pull_snapshot(n: int) -> pd.DataFrame:
    try:
        syms = list_universe(n=n)
    except TypeError:
        # in case function signature differs
        syms = list_universe(n)
    df = pull_enriched_snapshot(syms)
    try:
        df = fill_feature_gaps(df)
    except Exception:
        pass
    return _ensure_display_columns(df)

def render_dashboard_tab():
    st.subheader("BreakoutBuddy • Dashboard")
    n = int(st.session_state.get("universe_size", 500))
    topn = int(st.session_state.get("rows_to_display", 25))

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Refresh now (fetch & rank)", use_container_width=True):
            st.session_state["_bb_force_refresh"] = True

    df = _pull_snapshot(n)
    if df is None or df.empty:
        st.info("No snapshot available yet. Try **Refresh now**.")
        return

    # Display
    st.caption(f"Showing top N from Controls: {topn}")
    try:
        st.dataframe(df.head(topn), use_container_width=True)
    except Exception:
        st.write(df.head(topn))
