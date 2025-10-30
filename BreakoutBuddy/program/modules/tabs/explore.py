# program/modules/tabs/explore.py
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from pathlib import Path
import os

import pandas as pd  # type: ignore
import numpy as np  # type: ignore
import streamlit as st
from BreakoutBuddy.program.modules.ui.explain_addenda import render_advanced_explain

# Optional yfinance
try:
    import yfinance as yf  # type: ignore
except Exception:
    yf = None  # type: ignore

from modules.ui import quick_explain_page

APP_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("BREAKOUTBUDDY_DATA", APP_ROOT / "Data")).expanduser().resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------- helpers shared with dashboard ----------
def _calc_rsi4(close: pd.Series) -> pd.Series:
    c = pd.to_numeric(close, errors="coerce").fillna(method="ffill")
    delta = c.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(4).mean()
    roll_down = down.rolling(4).mean().replace(0, 1e-9)
    rs = roll_up / roll_down
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _load_universe_csv() -> List[str]:
    for nm in ("universe.csv","universe_tickers.csv","sp500.csv","nasdaq100.csv","russell1000.csv"):
        p = DATA_DIR / nm
        if p.exists():
            try:
                df = pd.read_csv(p)
                if "Ticker" in df.columns:
                    vals = [str(t).strip().upper() for t in df["Ticker"] if str(t).strip()]
                    if vals:
                        return vals
            except Exception:
                pass
    return []

_BUILTIN_UNIVERSE = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO","LLY","JPM","V","XOM",
    "UNH","WMT","MA","HD","PG","COST","JNJ","BAC","ORCL","MRK","NFLX","ABBV","KO",
    "PEP","ADBE","CRM","CSCO","AMD","CMCSA","NKE","MCD","DIS","PFE","WFC","AMAT",
    "QCOM","TXN","INTC","HON","UPS","CAT","RTX","IBM","CVX","SBUX",
]

def _universe(use_watchlist: bool) -> List[str]:
    uni = _load_universe_csv()
    if uni:
        return uni
    if use_watchlist:
        p = DATA_DIR / "watchlist.csv"
        if p.exists():
            try:
                df = pd.read_csv(p)
                if "Ticker" in df.columns:
                    vals = [str(t).strip().upper() for t in df["Ticker"] if str(t).strip()]
                    if vals:
                        return vals
            except Exception:
                pass
    return _BUILTIN_UNIVERSE[:]


def _fetch_one(t: str) -> Optional[dict]:
    if yf is None:
        return None
    try:
        hist = yf.Ticker(t).history(period="1mo", interval="1d", auto_adjust=False)
        if hist is None or hist.empty:
            return None
        hist = hist.reset_index()
        for need in ("Open","High","Low","Close","Volume"):
            if need not in hist.columns and need.title() in hist.columns:
                hist[need] = hist[need.title()]
        close = pd.to_numeric(hist["Close"], errors="coerce")
        vol = pd.to_numeric(hist["Volume"], errors="coerce")
        change_pct = close.pct_change() * 100.0
        rvol = vol / (vol.rolling(20).mean())
        rsi4 = _calc_rsi4(close)
        last = hist.iloc[-1]
        return {
            "Ticker": t,
            "Open": float(last["Open"]),
            "High": float(last["High"]),
            "Low": float(last["Low"]),
            "Close": float(last["Close"]),
            "Volume": float(last["Volume"]),
            "ChangePct": float(change_pct.iloc[-1]),
            "RVOL": float(rvol.iloc[-1]) if not np.isnan(rvol.iloc[-1]) else np.nan,
            "RSI4": float(rsi4.iloc[-1]) if not np.isnan(rsi4.iloc[-1]) else np.nan,
        }
    except Exception:
        return None


def _load_snapshot_from_disk() -> pd.DataFrame:
    for nm in ("explore_snapshot_latest.csv","snapshot.csv","ranked_latest.csv"):
        p = DATA_DIR / nm
        if p.exists():
            try:
                return pd.read_csv(p)
            except Exception:
                pass
    return pd.DataFrame()


def render_explore_tab(*, settings: Any = None, enrich_features_fn=None, **_kwargs) -> None:
    """Explore snapshot with fetch, filter, sort, and quick explain.
    Accepts **_kwargs to stay compatible with old app_main signatures (e.g., conn=...).
    """
    st.subheader("Explore Snapshot")

    with st.expander("Snapshot controls", expanded=True):
        st.caption(f"Data folder: `{DATA_DIR}`")
        use_watchlist = st.checkbox("Use watchlist as universe", value=False, key="explore_use_watchlist")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Load latest from disk", key="explore_load_disk"):
                df = _load_snapshot_from_disk()
                st.session_state["_explore_df"] = df
                st.success("Loaded latest snapshot from disk.")
        with col2:
            if st.button("Refresh from internet (yfinance)", key="explore_refresh_web"):
                if yf is None:
                    st.error("yfinance not installed in this environment.")
                else:
                    with st.spinner("Fetching..."):
                        rows = []
                        tickers = _universe(use_watchlist)[: int(st.session_state.get('controls_universe_size', 300) or 300) ]
                        for t in tickers:
                            rec = _fetch_one(t)
                            if rec:
                                rows.append(rec)
                        df = pd.DataFrame(rows)
                        if not df.empty:
                            for col in ["P_up","RelSPY","ConnorsRSI","SqueezeHint"]:
                                if col not in df.columns:
                                    df[col] = np.nan
                            df.to_csv(DATA_DIR / "explore_snapshot_latest.csv", index=False)
                        st.session_state["_explore_df"] = df
                    st.success("Snapshot refreshed and saved.")

    df = st.session_state.get("_explore_df")
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        df = _load_snapshot_from_disk()
    if df is None or df.empty:
        st.info("No snapshot found. Click 'Refresh from internet' above.")
        return

    # Sidebar-ish inline controls
    with st.expander("Filters & view", expanded=False):
        min_rvol = st.slider("Min RVOL", 0.0, 3.0, 0.0, 0.1, key="explore_min_rvol")
        min_chg = st.slider("Min ChangePct", -10.0, 10.0, -10.0, 0.1, key="explore_min_chg")
        search = st.text_input("Search ticker", "", key="explore_search")
        sort_by = st.selectbox("Sort by", options=[c for c in df.columns if c not in ("Date")], index=max(0, [c for c in df.columns].index("Combined") if "Combined" in df.columns else 0), key="explore_sort")
        ascending = st.checkbox("Ascending", value=False, key="explore_sort_asc")
        top_n = int(st.number_input("Show top N", min_value=5, max_value=500, value=int(st.session_state.get("controls_top_n", 25) or 25), step=1, key="explore_topn"))

    work = df.copy()
    if "RVOL" in work.columns:
        work = work[work["RVOL"].fillna(0) >= float(min_rvol)]
    if "ChangePct" in work.columns:
        work = work[work["ChangePct"].fillna(-999) >= float(min_chg)]
    if search.strip():
        sub = search.strip().upper()
        if "Ticker" in work.columns:
            work = work[work["Ticker"].astype(str).str.contains(sub, na=False)]
    if not work.empty and sort_by in work.columns:
        work = work.sort_values(by=sort_by, ascending=ascending)

    view = work.head(top_n) if not work.empty else work
    st.dataframe(view, use_container_width=True, hide_index=True)

    # === ADDED: Advanced Explain (Elliott Wave / Fib / Heikin Ashi) ===
    try:
        _tmp_df_for_explain = view
        import pandas as _pd
        if isinstance(_tmp_df_for_explain, _pd.DataFrame) and not _tmp_df_for_explain.empty:
            _syms_series = _tmp_df_for_explain.get("Ticker", _tmp_df_for_explain.get("Symbol"))
            if _syms_series is not None and len(_syms_series) > 0:
                _syms = sorted(set(_syms_series.astype(str)))
                with st.expander("📝 Explain a pick (advanced)", expanded=False):
                    _sym = st.selectbox("Symbol", _syms, key="explain_adv_sym_-9054165735620617570")
                    if _sym:
                        render_advanced_explain(_sym)
    except Exception:
        pass

    
    # Download filtered view
    if not view.empty:
        csv_bytes = view.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download filtered CSV",
            data=csv_bytes,
            file_name="explore_filtered.csv",
            mime="text/csv",
            key="explore_download_filtered"
        )

    st.markdown("---")
    default = str(view["Ticker"].iloc[0]) if "Ticker" in view.columns and len(view) else None
    quick_explain_page.render(df=view, default_ticker=default, show_header=True, key_prefix="explore")

