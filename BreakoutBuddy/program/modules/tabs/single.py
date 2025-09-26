# program/modules/tabs/single.py
from __future__ import annotations

from typing import Any, Optional
from pathlib import Path
import os
import pandas as pd  # type: ignore
import streamlit as st

# Optional yfinance for live fetch
try:
    import yfinance as yf  # type: ignore
except Exception:
    yf = None  # type: ignore

from modules.ui import quick_explain_page

APP_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("BREAKOUTBUDDY_DATA", APP_ROOT / "Data")).expanduser().resolve()
CACHE_DIR = DATA_DIR / "cache" / "ohlcv"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_from_cache(ticker: str) -> Optional[pd.DataFrame]:
    for pat in (f"{ticker}.csv", f"{ticker}_daily.csv", f"{ticker}-daily.csv"):
        p = CACHE_DIR / pat
        if p.exists():
            try:
                df = pd.read_csv(p)
                return df
            except Exception:
                pass
    return None


def _rsi4(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(method="ffill")
    delta = s.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(4).mean()
    roll_down = down.rolling(4).mean()
    rs = roll_up / (roll_down.replace(0, 1e-9))
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _load_single_ohlcv(ticker: str, period: str = "6mo") -> pd.DataFrame:
    t = ticker.strip().upper()
    df = _load_from_cache(t)
    if df is None and yf is not None:
        try:
            hist = yf.Ticker(t).history(period=period, interval="1d", auto_adjust=False)
            if not hist.empty:
                hist = hist.reset_index()
                hist.rename(columns=str.title, inplace=True)
                # Ensure standard column names
                for src, dst in [("Open","Open"),("High","High"),("Low","Low"),("Close","Close"),("Volume","Volume")]:
                    if src not in hist.columns and dst in hist.columns:
                        hist[src] = hist[dst]
                df = hist
        except Exception:
            df = None

    if df is None:
        return pd.DataFrame()

    # Compute ChangePct, RSI4 if missing
    if "ChangePct" not in df.columns and "Close" in df.columns:
        close = pd.to_numeric(df["Close"], errors="coerce")
        df["ChangePct"] = (close.pct_change() * 100).round(4)
    if "RSI4" not in df.columns and "Close" in df.columns:
        df["RSI4"] = _rsi4(df["Close"]).round(4)

    # Standardize column casing
    rename_map = {c: c.title() for c in df.columns}
    df = df.rename(columns=rename_map)
    return df


def render_single_tab(*, settings: Any = None):
    st.subheader("Single Ticker Analyzer")
    t = st.text_input("Ticker", value=st.session_state.get("single_ticker", "AAPL"), key="single_ticker_input")
    if st.button("Analyze", key="single_analyze"):
        st.session_state["single_ticker"] = t.strip().upper()

    ticker = st.session_state.get("single_ticker", t or "AAPL").strip().upper()
    df = _load_single_ohlcv(ticker)
    if df is None or df.empty:
        st.warning("No data returned for that symbol.")
        return

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Build a one-row DF for Quick Explain from the latest row
    latest = df.iloc[-1].to_dict()
    row = {
        "Ticker": ticker,
        "Open": latest.get("Open"),
        "High": latest.get("High"),
        "Low": latest.get("Low"),
        "Close": latest.get("Close"),
        "Volume": latest.get("Volume"),
        "ChangePct": latest.get("ChangePct"),
        "P_up": None,
        "RelSPY": None,
        "RVOL": latest.get("RVOL", None),
        "RSI4": latest.get("RSI4", None),
        "ConnorsRSI": latest.get("ConnorsRSI", None),
        "SqueezeHint": latest.get("SqueezeHint", None),
        "Combined": latest.get("Combined", None),
        "AgentBoost_exact": latest.get("AgentBoost_exact", None),
        "Combined_with_agents": latest.get("Combined_with_agents", None),
    }
    explain_df = pd.DataFrame([row])

    st.markdown("---")
    quick_explain_page.render(df=explain_df, default_ticker=ticker, show_header=True, key_prefix='single')
