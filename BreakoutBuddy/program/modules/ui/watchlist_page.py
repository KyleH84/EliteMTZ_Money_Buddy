from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

COLUMNS_ALL = [
    "Ticker","Open","High","Low","Close","Volume",
    "Combined","P_up","Risk","RelSPY","RVOL","RSI4","ConnorsRSI",
    "SqueezeHint","ChangePct","AgentBoost_exact","QuickWhy","RiskBadge"
]

def _data_dir() -> Path:
    here = Path(__file__).resolve()
    for up in [here, *here.parents]:
        cand = up / "Data"
        if cand.is_dir():
            return cand
        if up.name == "program":
            cand2 = up.parent / "Data"
            if cand2.is_dir():
                return cand2
    fb = here.parent / "Data"
    fb.mkdir(parents=True, exist_ok=True)
    return fb

def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except Exception:
        return 0.0

def _load_csv(name: str) -> tuple[pd.DataFrame, str, float]:
    p = _data_dir() / name
    if p.exists():
        try:
            df = pd.read_csv(p)
            ts = datetime.fromtimestamp(_mtime(p)).strftime("%Y-%m-%d %H:%M")
            return df, ts, _mtime(p)
        except Exception:
            return pd.DataFrame(), "", 0.0
    return pd.DataFrame(), "", 0.0

def _save_csv(df: pd.DataFrame, name: str):
    p = _data_dir() / name
    df.to_csv(p, index=False)

def _save_watchlist(df: pd.DataFrame):
    _save_csv(df, "watchlist.csv")

def _ensure_watchlist_file():
    p = _data_dir() / "watchlist.csv"
    if not p.exists():
        pd.DataFrame({ "Ticker": [] }).to_csv(p, index=False)

def _lift_chip(v: float) -> str:
    try:
        x = float(v)
        if x > 5: return "▲"
        if x < -5: return "▼"
        return ""
    except Exception:
        return ""

# --- Minimal enrich for missing tickers (no full pipeline required) ---
def _rsi(series: pd.Series, period: int = 4) -> float:
    s = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if len(s) < period + 1: 
        return 50.0
    delta = s.diff()
    up = delta.clip(lower=0.0).rolling(period).mean()
    down = (-delta.clip(upper=0.0)).rolling(period).mean()
    rs = up / (down + 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    try:
        return float(rsi.dropna().iloc[-1])
    except Exception:
        return 50.0

def _connors_rsi(close: pd.Series) -> float:
    s = pd.to_numeric(close, errors="coerce").dropna().astype(float)
    if len(s) < 10:
        return 50.0
    rsi4 = _rsi(s, 4)
    change = s.pct_change()
    streak = 0
    for i in range(1, len(change)):
        if change.iloc[-i] > 0:
            streak = streak + 1 if streak >= 0 else 1
        elif change.iloc[-i] < 0:
            streak = streak - 1 if streak <= 0 else -1
        else:
            break
    streak_vals = pd.Series([streak] * 15, dtype=float)
    streak_rsi = _rsi(streak_vals, 2)
    pct_rank = (pd.Series(change).rank(pct=True).iloc[-1] * 100.0) if change.notna().any() else 50.0
    return float((rsi4 + streak_rsi + pct_rank) / 3.0)

def _fetch_minimal_rows(tickers: list[str]) -> pd.DataFrame:
    try:
        import yfinance as yf
    except Exception:
        return pd.DataFrame(columns=COLUMNS_ALL)
    rows = []
    spy = None
    try:
        spy = yf.Ticker("SPY").history(period="7d")["Close"]
    except Exception:
        spy = None
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="60d")
            if hist is None or hist.empty:
                continue
            h = hist.tail(30).copy()
            h = h.rename(columns={c: c.split()[-1] for c in h.columns})
            close = pd.to_numeric(h.get("Close"), errors="coerce")
            open_ = pd.to_numeric(h.get("Open"), errors="coerce")
            high = pd.to_numeric(h.get("High"), errors="coerce")
            low = pd.to_numeric(h.get("Low"), errors="coerce")
            vol = pd.to_numeric(h.get("Volume"), errors="coerce")
            if close.notna().any():
                last_close = float(close.dropna().iloc[-1])
                last_open  = float(open_.dropna().iloc[-1]) if open_.notna().any() else last_close
                last_high  = float(high.dropna().iloc[-1]) if high.notna().any() else last_close
                last_low   = float(low.dropna().iloc[-1])  if low.notna().any() else last_close
                last_vol   = float(vol.dropna().iloc[-1])  if vol.notna().any() else 0.0
            else:
                continue
            prev_close = float(close.dropna().iloc[-2]) if close.dropna().shape[0] >= 2 else last_close
            change_pct = float((last_close - prev_close) / (prev_close if prev_close else last_close))
            avg_vol = float(vol.tail(20).mean()) if vol.notna().any() else 0.0
            rvol = float(last_vol / (avg_vol + 1e-9)) if avg_vol else 1.0
            rsi4 = _rsi(close, 4)
            crsi = _connors_rsi(close)
            if spy is not None and spy.notna().shape[0] >= 2 and close.dropna().shape[0] >= 2:
                relspy = float(close.pct_change().tail(5).mean() - spy.pct_change().tail(5).mean())
            else:
                relspy = 0.0
            rows.append({
                "Ticker": t,
                "Open": last_open,
                "High": last_high,
                "Low": last_low,
                "Close": last_close,
                "Volume": last_vol,
                "P_up": 0.5,
                "Risk": 0.0,
                "RelSPY": relspy,
                "RVOL": rvol,
                "RSI4": rsi4,
                "ConnorsRSI": crsi,
                "SqueezeHint": 0,
                "ChangePct": change_pct,
                "Combined": 0.0,
            })
        except Exception:
            continue
    return pd.DataFrame(rows)

def _ensure_explanations(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    try:
        from modules import explain as explain_mod
    except Exception:
        return df
    qs = []; rb = []
    for _, row in df.iterrows():
        try:
            exp = explain_mod.explain_for_row(row, allow_local_llm=True)
            qs.append(exp.get("quick",""))
            rb.append(exp.get("risk_badge",""))
        except Exception:
            qs.append("")
            rb.append("")
    out = df.copy()
    out["QuickWhy"] = qs
    out["RiskBadge"] = rb
    return out

def _order_cols(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in COLUMNS_ALL if c in df.columns]
    return df[cols] if cols else df

def add_to_watchlist(ticker: str):
    _ensure_watchlist_file()
    wl, _, _ = _load_csv("watchlist.csv")
    ticker = str(ticker).upper().strip()
    if ticker:
        if "Ticker" not in wl.columns:
            wl = pd.DataFrame({ "Ticker": [] })
        if ticker not in set(wl["Ticker"].astype(str)):
            wl = pd.concat([wl, pd.DataFrame({"Ticker": [ticker]})], ignore_index=True)
            _save_watchlist(wl)

def remove_from_watchlist(tickers: list[str]):
    _ensure_watchlist_file()
    wl, _, _ = _load_csv("watchlist.csv")
    if "Ticker" in wl.columns and tickers:
        wants = set(str(t).upper().strip() for t in tickers)
        wl = wl[~wl["Ticker"].astype(str).isin(wants)]
        _save_watchlist(wl)

def _rebuild_snapshot_if_needed(wl_df: pd.DataFrame, ranked_df: pd.DataFrame,
                                snap_df: pd.DataFrame, wl_m: float, ranked_m: float, snap_m: float) -> tuple[pd.DataFrame, str]:
    """If watchlist changed or ranked is newer or tickers mismatch, rebuild and persist snapshot.
    Also: if some watchlist tickers are missing from ranked, pull minimal rows for those so the user sees them immediately.
    """
    wl_set = set(wl_df["Ticker"].astype(str)) if "Ticker" in wl_df.columns else set()
    ranked_set = set(ranked_df["Ticker"].astype(str)) if "Ticker" in ranked_df.columns else set()
    snap_set = set(snap_df["Ticker"].astype(str)) if "Ticker" in snap_df.columns else set()

    need = False
    if snap_df.empty:
        need = True
    elif wl_set != snap_set:
        need = True
    elif ranked_m > snap_m or wl_m > snap_m:
        need = True

    if (need or True) and not wl_df.empty:
        base = pd.DataFrame()
        if not ranked_df.empty and "Ticker" in ranked_df.columns:
            base = ranked_df[ranked_df["Ticker"].astype(str).isin(wl_set)].copy()

        missing = sorted(list(wl_set - set(base["Ticker"].astype(str)) if "Ticker" in base.columns else wl_set))
        if missing:
            minimal = _fetch_minimal_rows(missing)
            if not minimal.empty:
                base = pd.concat([base, minimal], ignore_index=True) if not base.empty else minimal

        if not base.empty:
            base = base.drop_duplicates(subset=["Ticker"], keep="first")

        _save_csv(base, "watchlist_snapshot_latest.csv")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        return base, ts

    ts = datetime.fromtimestamp(snap_m).strftime("%Y-%m-%d %H:%M") if snap_m else ""
    return snap_df, ts

def render_watchlist_page(*, conn=None, settings=None, **kwargs):
    st.header("Watchlist")

    c1, c2 = st.columns([3,2])
    with c1:
        new_t = st.text_input("Add ticker to watchlist").upper().strip()
        if st.button("Add"):
            add_to_watchlist(new_t)
            st.success(f"Added {new_t}")
            st.rerun()
    with c2:
        wl, _, _ = _load_csv("watchlist.csv")
        rm = st.multiselect("Remove tickers", options=list(wl["Ticker"].astype(str)) if "Ticker" in wl.columns else [])
        if st.button("Remove selected"):
            remove_from_watchlist(rm)
            st.success("Removed.")
            st.rerun()

    wl, _, wl_m = _load_csv("watchlist.csv")
    ranked, _, ranked_m = _load_csv("ranked_latest.csv")
    snap, ts, snap_m = _load_csv("watchlist_snapshot_latest.csv")

    snap, ts = _rebuild_snapshot_if_needed(wl, ranked, snap, wl_m, ranked_m, snap_m)

    if snap.empty and ranked.empty:
        st.info("No watchlist snapshot yet and no ranked data available. Run a rank once.")
        return

    wl_set = set(wl["Ticker"].astype(str)) if "Ticker" in wl.columns else set()
    snap_set = set(snap["Ticker"].astype(str)) if "Ticker" in snap.columns else set()
    missing = sorted(list(wl_set - snap_set))
    if missing:
        st.warning(f"Unavailable or delisted tickers skipped: {', '.join(missing)}.")

    if "AgentBoost_exact" not in snap.columns or "Combined_with_agents" not in snap.columns:
        try:
            from modules.services import agents_service as AS
            snap = AS.enrich_scores(snap)
        except Exception:
            if "AgentBoost_exact" not in snap.columns:
                snap["AgentBoost_exact"] = 0.0
            if "Combined_with_agents" not in snap.columns:
                snap["Combined_with_agents"] = snap.get("Combined", 0.0)

    st.caption(f"Last updated: {ts or 'n/a'} • Universe: {len(snap)} rows")
    snap["Lift"] = snap["AgentBoost_exact"].apply(lambda v: "▲" if float(v) > 5 else ("▼" if float(v) < -5 else ""))

    try:
        from modules import explain as explain_mod
        qs = []; rb = []
        for _, row in snap.iterrows():
            exp = explain_mod.explain_for_row(row, allow_local_llm=True)
            qs.append(exp.get("quick","")); rb.append(exp.get("risk_badge",""))
        snap["QuickWhy"] = qs; snap["RiskBadge"] = rb
    except Exception:
        pass

    cols = [c for c in COLUMNS_ALL if c in snap.columns]
    view = snap[cols] if cols else snap
    st.dataframe(view, height=520, width='stretch')

    if not snap.empty and "Ticker" in snap.columns:
        tickers = list(snap["Ticker"].astype(str))
        sel = st.selectbox("Focus", options=tickers)
        if sel:
            row = snap[snap["Ticker"].astype(str) == sel].iloc[0].to_dict()
            try:
                from modules import explain as explain_mod
                exp = explain_mod.explain_for_row(row, allow_local_llm=True)
                st.markdown("### Why (detailed)")
                st.write(exp.get("detailed",""))
            except Exception:
                st.info("Explanation module unavailable.")

def render(*args, **kwargs):
    return render_watchlist_page(*args, **kwargs)
