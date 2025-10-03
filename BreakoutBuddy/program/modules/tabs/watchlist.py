from __future__ import annotations
from typing import List
import pandas as pd
import streamlit as st

from BreakoutBuddy.program.modules.data import pull_enriched_snapshot
from BreakoutBuddy.program.modules.services import newswire_local

def render_watchlist_tab(*, conn=None, settings=None, pull_enriched_snapshot_fn=None, enrich_features_fn=None):
    st.subheader("Watchlist")
    raw = st.text_area("Watchlist symbols (comma/space separated)", key="watchlist_symbols_text")
    syms: List[str] = newswire_local.parse_ticker_text(raw)
    if st.button("Load snapshot for watchlist"):
        if not syms:
            st.warning("Add at least one ticker.")
            return
        fn = pull_enriched_snapshot_fn or pull_enriched_snapshot
        df = fn(syms)
        if enrich_features_fn is not None:
            try:
                df = enrich_features_fn(df)
            except Exception:
                pass
        if df is None or df.empty:
            st.info("No data for the provided symbols.")
            return
        st.session_state["watchlist_df"] = df

    df = st.session_state.get("watchlist_df")
    if isinstance(df, pd.DataFrame) and not df.empty:
        st.dataframe(df, use_container_width=True)
