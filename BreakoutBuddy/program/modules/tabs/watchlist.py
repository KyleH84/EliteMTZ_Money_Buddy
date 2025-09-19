from __future__ import annotations
import streamlit as st
from modules.ui.watchlist_page import render as render_watchlist_page

def render_watchlist_tab(
    *,
    conn,
    settings,
    pull_enriched_snapshot_fn,
    enrich_features_fn,
    train_online_fn=None,
    score_snapshot_fn=None,
):
    st.subheader("Watchlist")
    render_watchlist_page(
        conn=conn,
        settings=settings,
        pull_enriched_snapshot_fn=pull_enriched_snapshot_fn,
        enrich_features_fn=enrich_features_fn,
        train_online_fn=train_online_fn,
        score_snapshot_fn=score_snapshot_fn,
        header=False,
    )
