from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

# Columns we want present & numeric
REQUIRED = ["P_up","ConnorsRSI","SqueezeHint","RelSPY","RVOL","RSI4","ChangePct","Close"]

def _rsi(s: pd.Series, n: int) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - (100/(1+rs))

def _connors_rsi(close: pd.Series) -> pd.Series:
    rsi2 = _rsi(close, 2)
    rsi4 = _rsi(close, 4)
    chg = close.pct_change().fillna(0)
    pr100 = chg.rolling(100).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1]*100, raw=False)
    diff = close.diff()
    streak = (np.sign(diff) != np.sign(diff.shift())).cumsum()
    streak = (streak.groupby(streak).cumcount()+1)*np.sign(diff).fillna(0)
    streak_rsi = _rsi(streak, 2)
    return pd.concat([rsi2, rsi4, pr100.fillna(50), streak_rsi.fillna(50)], axis=1).mean(axis=1)

def _fetch_latest(tickers: list[str]) -> pd.DataFrame:
    try:
        import yfinance as yf
    except Exception:
        return pd.DataFrame(columns=["Ticker"]+REQUIRED)

    t = [x.strip().upper() for x in tickers if x]
    if not t:
        return pd.DataFrame(columns=["Ticker"]+REQUIRED)

    all_syms = sorted(set(t)|{"SPY"})
    end = datetime.utcnow().date()
    start = end - timedelta(days=120)
    data = yf.download(all_syms, start=start.isoformat(), end=end.isoformat(),
                       interval="1d", auto_adjust=False, progress=False, threads=False)

    if isinstance(data.columns, pd.MultiIndex):
        close = data["Adj Close"] if "Adj Close" in data.columns.levels[0] else data["Close"]
        vol = data["Volume"]
    else:
        close = data["Adj Close"].to_frame() if "Adj Close" in data else data["Close"].to_frame()
        vol = data["Volume"].to_frame()

    out = []
    for sym in t:
        cs = close.get(sym, pd.Series(dtype=float)).dropna()
        vs = vol.get(sym, pd.Series(dtype=float)).dropna()
        if cs.empty:
            out.append({"Ticker": sym})
            continue

        spy = close.get("SPY", pd.Series(dtype=float)).dropna()
        change_pct = (cs.iloc[-1]/cs.iloc[-2]-1)*100 if len(cs) > 1 else 0.0
        relspy = (cs.pct_change().iloc[-1] - spy.pct_change().iloc[-1]) if (len(cs)>1 and len(spy)>1) else 0.0
        rsi4 = _rsi(cs, 4).iloc[-1] if len(cs) > 5 else 50.0
        crsi = _connors_rsi(cs).iloc[-1] if len(cs) > 20 else 50.0
        avg5 = vs.rolling(5).mean().iloc[-1] if len(vs) >= 5 else 1.0
        rvol = (vs.iloc[-1]/avg5) if avg5 else 1.0

        out.append({
            "Ticker": sym,
            "Close": float(cs.iloc[-1]),
            "ChangePct": float(round(change_pct, 4)),
            "RelSPY": float(round(relspy, 4)),
            "RSI4": float(round(rsi4, 2)),
            "ConnorsRSI": float(round(crsi, 2)),
            "RVOL": float(round(rvol, 3)),
            "P_up": 0.55,
            "SqueezeHint": 0.0,
        })
    return pd.DataFrame(out)

def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    # replace literal "None" strings -> NaN, then fill & numeric
    for col in REQUIRED:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = df[col].replace("None", np.nan)
    fills = {
        "P_up": 0.55, "ConnorsRSI": 50.0, "SqueezeHint": 0.0, "RelSPY": 0.0,
        "RVOL": 1.0, "RSI4": 50.0, "ChangePct": 0.0, "Close": 0.0
    }
    for c, d in fills.items():
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(d)
    return df

def ensure_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure REQUIRED columns exist with real values.
    - Any missing/NaN/"None" values are fetched from yfinance for those tickers.
    - Final DF is numeric & filled (no literal "None" strings).
    """
    if df is None or df.empty or "Ticker" not in df.columns:
        return df

    # normalize casing & dedupe
    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df = df.drop_duplicates(subset=["Ticker"], keep="last")

    # mark which tickers need fetching
    need = []
    for _, row in df.iterrows():
        missing = any((col not in df.columns) or pd.isna(row.get(col)) or str(row.get(col)) == "None" for col in REQUIRED)
        if missing:
            need.append(row["Ticker"])

    if need:
        fresh = _fetch_latest(need)
        if not fresh.empty:
            df = df.merge(fresh, on="Ticker", how="left", suffixes=("", "_fresh"))
            # prefer fresh values if existing are NaN/"None"
            for col in REQUIRED:
                f = col + "_fresh"
                if f in df.columns:
                    base = df[col] if col in df.columns else pd.Series([np.nan]*len(df))
                    df[col] = base.replace("None", np.nan).combine_first(df[f])
            # cleanup
            drop_cols = [c for c in df.columns if c.endswith("_fresh")]
            if drop_cols:
                df = df.drop(columns=drop_cols, errors="ignore")

    return _coerce_numeric(df)

# Back-compat alias
def enrich_features(df: pd.DataFrame) -> pd.DataFrame:
    return ensure_features(df)