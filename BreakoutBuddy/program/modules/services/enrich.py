
from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

EXPECTED_FEATURES = [
    "Close","ChangePct","RSI2","RSI4","ConnorsRSI","RelSPY",
    "RVOL","ATR","PctFrom200d","SqueezeHint","P_up",
    "CrowdRisk","AgentsScore","AgentsConf"
]

def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = (delta.clip(lower=0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _percent_rank(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100, raw=False)

def _connors_rsi(close: pd.Series) -> pd.Series:
    rsi2 = _rsi(close, 2)
    rsi4 = _rsi(close, 4)
    diff = close.diff()
    streak = (np.sign(diff) != np.sign(diff.shift())).cumsum()
    streak = (streak.groupby(streak).cumcount() + 1) * np.sign(diff).fillna(0)
    streak_rsi = _rsi(streak.fillna(0), 2)
    pr = _percent_rank(close.pct_change().fillna(0), 100)
    return (rsi2 + rsi4 + pr.fillna(50) + streak_rsi.fillna(50)) / 4

def _fetch_latest_features(tickers: list[str]) -> pd.DataFrame:
    try:
        import yfinance as yf
    except Exception:
        return pd.DataFrame(columns=["Ticker"] + EXPECTED_FEATURES)

    tickers = [t for t in dict.fromkeys([str(t).upper().strip() for t in tickers]) if t]
    if not tickers:
        return pd.DataFrame(columns=["Ticker"] + EXPECTED_FEATURES)

    # Always include SPY for RelSPY
    all_syms = sorted(set(tickers) | {"SPY"})
    end = datetime.utcnow().date()
    start = end - timedelta(days=120)
    data = yf.download(all_syms, start=start.isoformat(), end=end.isoformat(), interval="1d", auto_adjust=False, progress=False, threads=False)

    if isinstance(data.columns, pd.MultiIndex):
        close = data["Adj Close"].copy() if "Adj Close" in data.columns.levels[0] else data["Close"].copy()
        vol = data["Volume"].copy()
    else:
        close = data["Adj Close"].to_frame()
        vol = data["Volume"].to_frame()

    features = []
    for t in tickers:
        c = close[t].dropna() if t in close.columns else pd.Series(dtype=float)
        v = vol[t].dropna() if t in vol.columns else pd.Series(dtype=float)
        if c.empty:
            row = {"Ticker": t}
        else:
            chg = c.pct_change().iloc[-1] if len(c) > 1 else 0.0
            spy_c = close["SPY"].dropna() if "SPY" in close.columns else pd.Series(dtype=float)
            relspy = (c.pct_change().iloc[-1] - spy_c.pct_change().iloc[-1]) if len(c) > 1 and not spy_c.empty else 0.0
            rsi2 = _rsi(c, 2).iloc[-1] if len(c) > 5 else 50.0
            rsi4 = _rsi(c, 4).iloc[-1] if len(c) > 5 else 50.0
            crsi = _connors_rsi(c).iloc[-1] if len(c) > 20 else 50.0
            avg20 = v.rolling(20).mean().iloc[-1] if len(v) >= 20 else 1.0
            rvol = (v.iloc[-1] / avg20) if avg20 and avg20 != 0 else 1.0
            atr = (c.rolling(14).std().iloc[-1] * np.sqrt(14)) if len(c) >= 14 else 0.0
            pct200 = ((c.iloc[-1] / c.rolling(200).mean().iloc[-1]) - 1.0) * 100 if len(c) >= 200 else 0.0
            squeeze = 0.0
            row = {
                "Ticker": t, "Close": float(c.iloc[-1]), "ChangePct": float(chg * 100.0),
                "RSI2": float(rsi2), "RSI4": float(rsi4), "ConnorsRSI": float(crsi),
                "RelSPY": float(relspy), "RVOL": float(rvol), "ATR": float(atr),
                "PctFrom200d": float(pct200), "SqueezeHint": float(squeeze),
                "P_up": 0.55,
            }
        features.append(row)

    df = pd.DataFrame(features).drop_duplicates(subset=["Ticker"], keep="last")
    return df

def ensure_features(merged: pd.DataFrame) -> pd.DataFrame:
    need = []
    need_cols = ["RelSPY","ConnorsRSI","SqueezeHint","P_up","RVOL","RSI4","ChangePct","Close"]
    for _, row in merged.iterrows():
        t = str(row.get("Ticker","")).strip().upper()
        if not t:
            continue
        missing = any((col not in merged.columns) or pd.isna(row.get(col)) for col in need_cols)
        if missing:
            need.append(t)
    if not need:
        return merged

    fetched = _fetch_latest_features(need)
    if not fetched.empty:
        merged = merged.drop_duplicates(subset=["Ticker"], keep="last")
        merged = merged.merge(fetched, on="Ticker", how="left", suffixes=('', '_fresh'))
        for col in EXPECTED_FEATURES:
            fresh = col + "_fresh"
            if fresh in merged.columns:
                merged[col] = merged[col].combine_first(merged[fresh])
        merged = merged[[c for c in merged.columns if not c.endswith("_fresh")]]

    defaults = {
        "Close": 0.0, "ChangePct": 0.0, "RSI2": 50.0, "RSI4": 50.0,
        "ConnorsRSI": 50.0, "RelSPY": 0.0, "RVOL": 1.0, "ATR": 0.0,
        "PctFrom200d": 0.0, "SqueezeHint": 0.0, "P_up": 0.55,
        "CrowdRisk": 0.0, "AgentsScore": None, "AgentsConf": None,
    }
    for c, d in defaults.items():
        if c not in merged.columns:
            merged[c] = d
        merged[c] = pd.to_numeric(merged[c], errors='coerce') if isinstance(d, (int,float)) else merged[c]
        merged[c] = merged[c].fillna(d)

    return merged

# --- Backward-compat shim ---
def enrich_features(merged):
    """Compatibility alias for older imports expecting 'enrich_features'.
    Delegates to ensure_features(merged)."""
    return ensure_features(merged)
