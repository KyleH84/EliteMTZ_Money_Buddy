from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import streamlit as st

# --- Unified data fill (no UI change) ---
try:
    from BreakoutBuddy.program.utilities.feature_fixups import ensure_basic_indicators
except Exception:
    ensure_basic_indicators = None

def _bb_unify(view):
    import pandas as _pd, numpy as _np
    if view is None or view.empty:
        return view
    # % +/- from ChangePct or Open/Close
    if "% +/-" not in view.columns:
        if "ChangePct" in view.columns:
            s = _pd.to_numeric(view["ChangePct"], errors="coerce")
            view["% +/-"] = s
        elif {"Open","Close"}.issubset(view.columns):
            o = _pd.to_numeric(view["Open"], errors="coerce")
            c = _pd.to_numeric(view["Close"], errors="coerce")
            view["% +/-"] = (c - o) / o * 100.0
    # Ensure indicators
    if ensure_basic_indicators is not None:
        try:
            view = ensure_basic_indicators(view)
        except Exception:
            pass
    # RiskBadge from RVOL/Volume
    if "RiskBadge" not in view.columns:
        try:
            rvol = _pd.to_numeric(view.get("RVOL", _pd.Series([], dtype=float)), errors="coerce")
            if rvol is not None and len(rvol):
                view["RiskBadge"] = rvol.apply(lambda r: "High Volume" if r>=1.5 else ("Medium Volume" if r>=1.1 else "Low Volume"))
            else:
                vol = _pd.to_numeric(view.get("Volume", _pd.Series([], dtype=float)), errors="coerce")
                view["RiskBadge"] = vol.apply(lambda v: "High Volume" if v>=1e8 else ("Medium Volume" if v>=5e7 else "Low Volume"))
        except Exception:
            pass
    # Column order
    want = ["Ticker","Open","High","Low","Close","Volume","% +/-","RSI4","ConnorsRSI","RelSPY","RVOL","ATR","PctFrom200d","SqueezeHint","RiskBadge"]
    have = [c for c in want if c in view.columns]
    if have:
        view = view[h ave]
    return view
# --- end unified data fill ---
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
