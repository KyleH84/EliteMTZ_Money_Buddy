# program/modules/tabs/dashboard.py
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


# ----------------------- Universe selection -----------------------
_BUILTIN_UNIVERSE = [
    # Mega/large caps + liquid names (about 60)
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO","BRK-B","LLY","JPM","V","XOM","UNH","WMT",
    "MA","HD","PG","COST","JNJ","BAC","ORCL","MRK","NFLX","ABBV","KO","PEP","ADBE","CRM","CSCO","AMD",
    "TM","TMO","LIN","CMCSA","NKE","MCD","DIS","PFE","WFC","ABNB","AMAT","QCOM","TXN","INTC","HON","UPS",
    "CAT","RTX","IBM","CVX","SBUX","SPY","QQQ","META","NVDA","AMZN","AAPL","MSFT","GOOGL","TSLA","AMD",
]

def _load_universe_csv() -> List[str]:
    # Look for common universe files in Data/
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

def _universe_candidates(use_watchlist: bool) -> List[str]:
    # Primary: explicit universe.csv (or similar)
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
    # Fallback: built-in broad universe
    return _BUILTIN_UNIVERSE[:]


# ----------------------- Feature calc -----------------------
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

def _fetch_one(t: str) -> Optional[dict]:
    if yf is None:
        return None
    try:
        hist = yf.Ticker(t).history(period="1mo", interval="1d", auto_adjust=False)
        if hist is None or hist.empty or len(hist) < 5:
            return None
        hist = hist.reset_index()
        # ensure columns
        for need in ("Open","High","Low","Close","Volume"):
            if need not in hist.columns and need.title() in hist.columns:
                hist[need] = hist[need.title()]
        # compute features
        close = pd.to_numeric(hist["Close"], errors="coerce")
        vol = pd.to_numeric(hist["Volume"], errors="coerce")
        change_pct = close.pct_change() * 100.0
        rvol = vol / (vol.rolling(20).mean())
        rsi4 = _calc_rsi4(close)

        last = hist.iloc[-1]
        row = {
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
        return row
    except Exception:
        return None

def _rank_now(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # RelSPY vs SPY
    try:
        if yf is not None:
            spy = yf.Ticker("SPY").history(period="1mo", interval="1d", auto_adjust=False)
            if not spy.empty:
                cp = spy["Close"].pct_change() * 100.0
                out["RelSPY"] = out["ChangePct"] - float(cp.iloc[-1])
            else:
                out["RelSPY"] = 0.0
        else:
            out["RelSPY"] = 0.0
    except Exception:
        out["RelSPY"] = 0.0

    # Combined score: z(ChangePct) + z(RVOL) + z(RelSPY)
    for col in ("ChangePct","RVOL","RelSPY"):
        out[col] = pd.to_numeric(out.get(col), errors="coerce")
    z = lambda s: (s - s.mean()) / (s.std() or 1.0)
    out["Combined"] = z(out["ChangePct"].fillna(0)) + z(out["RVOL"].fillna(0)) + z(out["RelSPY"].fillna(0))
    out["AgentBoost_exact"] = 0.0
    out["Combined_with_agents"] = out["Combined"]
    return out.sort_values("Combined", ascending=False).reset_index(drop=True)


def _scan_and_save(limit: int, use_watchlist: bool) -> Tuple[pd.DataFrame, pd.DataFrame]:
    tickers = _universe_candidates(use_watchlist)[:max(1, limit)]
    rows = []
    for t in tickers:
        r = _fetch_one(t)
        if r:
            rows.append(r)
    snap = pd.DataFrame(rows)
    if not snap.empty:
        for col in ["P_up","ConnorsRSI","SqueezeHint"]:
            if col not in snap.columns:
                snap[col] = np.nan
        snap.to_csv(DATA_DIR / "explore_snapshot_latest.csv", index=False)
        ranked = _rank_now(snap)
        ranked.to_csv(DATA_DIR / "ranked_latest.csv", index=False)
    else:
        ranked = pd.DataFrame()
    return snap, ranked


def _load_ranked_from_disk() -> pd.DataFrame:
    for nm in ("ranked_latest.csv","ranked.csv","explore_snapshot_latest.csv"):
        p = DATA_DIR / nm
        if p.exists():
            try:
                return pd.read_csv(p)
            except Exception:
                pass
    return pd.DataFrame()


def render_dashboard_tab(*, settings: Any = None, has_agents: bool = False) -> None:
    st.markdown("### BreakoutBuddy ▸ Dashboard")
    st.caption("Top ranked from today's Explore snapshot.")

    with st.expander("Snapshot controls", expanded=True):
        st.write("Data folder:", f"`{DATA_DIR}`")
        # New: toggle to use watchlist vs full universe
        use_watchlist = st.checkbox("Use watchlist as universe (instead of full universe)", value=False, key="dash_use_watchlist")

        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Load latest from disk", key="dash_load_disk"):
                df = _load_ranked_from_disk()
                st.session_state["_dash_ranked_df"] = df
                st.success("Loaded from disk.")
        with col2:
            if st.button("Refresh now (fetch & rank with yfinance)", key="dash_refresh_yf"):
                if yf is None:
                    st.error("yfinance is not installed in this environment.")
                else:
                    with st.spinner("Fetching latest data, please wait..."):
                        snap, ranked = _scan_and_save(
                            limit=int(st.session_state.get("controls_universe_size", 300) or 300),
                            use_watchlist=use_watchlist,
                        )
                        st.session_state["_dash_ranked_df"] = ranked
                    st.success("Refreshed from internet and saved CSVs.")

    # Top N
    top_n = int(st.session_state.get("controls_top_n", 25) or 25)
    st.caption(f"Showing top N from Controls: {top_n}")

    df = st.session_state.get("_dash_ranked_df")
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        df = _load_ranked_from_disk()
    if df is None or df.empty:
        st.info("No ranked data yet. Click **Refresh now** to fetch from the internet, or **Load latest from disk**.")
        return

    view = df.copy().head(top_n)
    desired = [
        "Ticker","Open","High","Low","Close","Volume","ChangePct",
        "P_up","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint",
        "Combined","AgentBoost_exact","Combined_with_agents",
    ]
    show_cols = [c for c in desired if c in view.columns] + [c for c in view.columns if c not in desired]
    st.dataframe(view[show_cols], use_container_width=True, hide_index=True)

    # === ADDED: Advanced Explain (Elliott Wave / Fib / Heikin Ashi) ===
    try:
        _tmp_df_for_explain = view[show_cols]
        import pandas as _pd
        if isinstance(_tmp_df_for_explain, _pd.DataFrame) and not _tmp_df_for_explain.empty:
            _syms_series = _tmp_df_for_explain.get("Ticker", _tmp_df_for_explain.get("Symbol"))
            if _syms_series is not None and len(_syms_series) > 0:
                _syms = sorted(set(_syms_series.astype(str)))
                with st.expander("📝 Explain a pick (advanced)", expanded=False):
                    _sym = st.selectbox("Symbol", _syms, key="explain_adv_sym_3913864280222426217")
                    if _sym:
                        render_advanced_explain(_sym)
    except Exception:
        pass

    st.markdown("---")
    default = str(view["Ticker"].iloc[0]) if "Ticker" in view.columns and len(view) else None
    quick_explain_page.render(df=view, default_ticker=default, show_header=True, key_prefix='dash')
