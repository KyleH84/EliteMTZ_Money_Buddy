# program/modules/ui/watchlist_page.py
from __future__ import annotations

from typing import Any, Optional, List
from pathlib import Path
import os
import pandas as pd  # type: ignore
import streamlit as st

from modules import watchlist as wlmod
from . import quick_explain_page

APP_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("BREAKOUTBUDDY_DATA", APP_ROOT / "Data")).expanduser().resolve()
WATCHLIST_CSV = DATA_DIR / "watchlist.csv"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _read_watchlist() -> List[str]:
    if WATCHLIST_CSV.exists():
        try:
            df = pd.read_csv(WATCHLIST_CSV)
            if "Ticker" in df.columns:
                return [str(t).strip().upper() for t in df["Ticker"] if str(t).strip()]
        except Exception:
            pass
    return []

def _write_watchlist(tickers: List[str]) -> None:
    uniq = sorted(set([str(t).strip().upper() for t in tickers if str(t).strip()]))
    pd.DataFrame({"Ticker": uniq}).to_csv(WATCHLIST_CSV, index=False)

def render(*, conn=None, settings: Any = None, enrich_features_fn=None, header: bool = True):
    if header:
        st.subheader("Watchlist")

    current = _read_watchlist()

    with st.expander("Manage watchlist", expanded=False):
        colA, colB = st.columns([3,1])
        with colA:
            new_t = st.text_input("Add ticker", placeholder="e.g. AAPL, NVDA", key="wl_add_input")
        with colB:
            if st.button("Add", key="wl_add_btn"):
                extra = [x.strip().upper() for x in new_t.split(",") if x.strip()]
                _write_watchlist(current + extra)
                st.success(f"Added: {', '.join(extra)}")
                st.experimental_rerun()
        if current:
            rm = st.multiselect("Remove tickers", options=current, key="wl_rm_multi")
            if st.button("Remove selected", key="wl_rm_btn"):
                remaining = [t for t in current if t not in set(rm)]
                _write_watchlist(remaining)
                st.success("Removed selected symbols.")
                st.experimental_rerun()

    tickers = _read_watchlist()
    if not tickers:
        st.info("Watchlist is empty. Add some tickers above.")
        return

    try:
        df = wlmod.enriched_snapshot(tickers, enrich_features_fn=enrich_features_fn)
    except Exception as e:
        st.error(f"Failed to score watchlist: {e}")
        return

    if df is None or df.empty:
        st.info("No data available for watchlist.")
        return

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Quick explain on the current watchlist snapshot
    st.markdown("---")
    default = str(df["Ticker"].iloc[0]) if "Ticker" in df.columns and len(df) else None
    quick_explain_page.render(df=df, default_ticker=default, show_header=True)
