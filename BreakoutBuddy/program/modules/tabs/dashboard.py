from __future__ import annotations
# program/modules/tabs/dashboard.py
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from pathlib import Path
import os

import pandas as pd  # type: ignore
import numpy as np  # type: ignore
from typing import Optional, List, Dict, Any
try:
    from ..services.enrich import enrich_features
except Exception:
    enrich_features = None  # type: ignore
try:
    from ..services.persistence_supabase import save_table, load_table
except Exception:
    save_table = load_table = None  # type: ignore

import streamlit as st
from utilities.feature_fixups import fill_feature_gaps
from data.spy_loader import get_spy_prices

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


# ---- Supabase history append helpers ----
def _append_supabase_history(kind: str, df: 'pd.DataFrame', app: str = 'BB') -> None:
    if save_table is None or load_table is None or df is None or df.empty:
        return
    try:
        date_str = pd.Timestamp.utcnow().strftime('%Y-%m-%d')
        name = f"history/{kind}_{date_str}"
        try:
            existing = load_table(name, app=app)
        except Exception:
            existing = None
        if existing is not None and not existing.empty:
            cols = [c for c in ['Ticker','Date','Datetime','AsOf','Close'] if c in df.columns]
            if cols:
                merged = pd.concat([existing, df], ignore_index=True).drop_duplicates(subset=cols, keep='last')
            else:
                merged = pd.concat([existing, df], ignore_index=True).drop_duplicates(keep='last')
            save_table(name, merged, app=app)
        else:
            save_table(name, df, app=app)
    except Exception:
        pass


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
        try:
            if enrich_features is not None:
                snap = enrich_features(snap)
        # --- Post-enrich safeguard: ensure feature columns exist (avoid blanks in table)
        try:
            _need_cols = ["P_up","ConnorsRSI","SqueezeHint","AgentBoost_exact"]
            for _c in _need_cols:
                if _c not in snap.columns:
                    snap[_c] = None
            # Fill obvious NAs to safe defaults for display
            snap["AgentBoost_exact"] = snap["AgentBoost_exact"].fillna(0)
            for _c in ["P_up","ConnorsRSI","SqueezeHint"]:
                snap[_c] = snap[_c].fillna("None")
        except Exception:
            pass
        except Exception:
            pass
        for col in ["P_up","ConnorsRSI","SqueezeHint"]:
            if col not in snap.columns:
                snap[col] = np.nan
        snap.to_csv(DATA_DIR / "explore_snapshot_latest.csv", index=False)
        ranked = _rank_now(snap)
    # Save latest and append history to Supabase (non-fatal if not configured)
    try:
        if save_table is not None:
            save_table('snapshot_latest', snap, app='BB')
            save_table('ranked_latest', ranked if 'ranked' in locals() else snap, app='BB')
            _append_supabase_history('snapshot', snap, app='BB')
            _append_supabase_history('ranked', ranked if 'ranked' in locals() else snap, app='BB')
    except Exception:
        pass
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

    try:
        df = fill_feature_gaps(df, spy_ref=get_spy_prices())
    except Exception as _ffg_e:
        pass

    view = df.copy().head(top_n)
    desired = [
        "Ticker","Open","High","Low","Close","Volume","ChangePct",
        "P_up","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint",
        "Combined","AgentBoost_exact","Combined_with_agents",
    ]
    show_cols = [c for c in desired if c in view.columns] + [c for c in view.columns if c not in desired]
    st.dataframe(view[show_cols], use_container_width=True, hide_index=True)

    st.markdown("---")
    default = str(view["Ticker"].iloc[0]) if "Ticker" in view.columns and len(view) else None
    quick_explain_page.render(df=view, default_ticker=default, show_header=True, key_prefix='dash')