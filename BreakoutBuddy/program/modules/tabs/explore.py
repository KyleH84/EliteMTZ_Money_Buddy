from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import streamlit as st
from pathlib import Path
import pandas as pd
from modules import explain as explain_mod

def render_explore_tab(
    *,
    settings,
    list_universe_fn,
    pull_enriched_snapshot_fn,
    enrich_features_fn,
):
    st.subheader("Explore Snapshot")
    DATA_DIR = Path("Data")
    snap_path = DATA_DIR / "snapshot_latest.csv"

    # Try CSV first
    snap = None
    if snap_path.exists():
        try:
            snap = pd.read_csv(snap_path)
        except Exception:
            snap = None

    # Optional refresh button
    do_refresh = st.button("Refresh snapshot", key="explore_refresh", type="primary")

    if do_refresh or snap is None or snap.empty:
        with st.spinner("Pulling snapshot…"):
            try:
                syms = list_universe_fn(getattr(settings, "universe_size", 300))
                snap = pull_enriched_snapshot_fn(syms)
                # Persist
                try:
                    snap.to_csv(snap_path, index=False)
                except Exception:
                    pass
            except Exception as e:
                st.error(f"Snapshot pull failed: {e}")
                snap = None

    if snap is None or snap.empty:
        st.info("No snapshot available yet. Visit Dashboard once or click Refresh.")
        return

    # Display sections
    cols = ["Ticker","Open","High","Low","Close","Volume","ChangePct","P_up","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint"]
    view = snap[[c for c in cols if c in snap.columns]].copy() if isinstance(snap, pd.DataFrame) else snap
    st.dataframe(view, width="stretch", hide_index=True)

    # Movers and RVOL
    try:
        if "ChangePct" in snap.columns:
            top_up = snap.sort_values("ChangePct", ascending=False).head(15)
            st.write("Top daily movers")
            st.dataframe(top_up[[c for c in ["Ticker","Close","ChangePct","RVOL","RSI4"] if c in top_up.columns]], width="stretch", hide_index=True)
        if "RVOL" in snap.columns:
            top_rvol = snap.sort_values("RVOL", ascending=False).head(15)
            st.write("Highest RVOL")
            st.dataframe(top_rvol[[c for c in ["Ticker","Close","RVOL","ChangePct","RSI4"] if c in top_rvol.columns]], width="stretch", hide_index=True)
    except Exception:
        pass

    # Plain English
    try:
        expl = explain_mod.explain_scan(snap, top_n=min(20, len(snap)))
        st.text_area("Plain English quick read", expl, height=300)
    except Exception:
        pass
