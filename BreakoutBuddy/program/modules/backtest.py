from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import pandas as pd
import numpy as np
import yfinance as yf

def _rsi(series: pd.Series, n:int=14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    down = -delta.clip(upper=0).ewm(alpha=1/n, adjust=False).mean()
    rs = up / (down.replace(0, np.nan))
    rsi = 100 - (100/(1+rs))
    return rsi.fillna(50)

def quick_backtest_rsi2_rule(tickers, rsi2_thresh:int=5, horizon:int=5, target_pct:float=3.0) -> pd.DataFrame:
    rows = []
    for t in tickers:
        df = yf.download(t, period="2y", interval="1d", auto_adjust=False, progress=False)
        if df is None or df.empty: 
            continue
        df["RSI2"] = _rsi(df["Close"], 2)
        sig = df["RSI2"] < rsi2_thresh
        runup = df["Close"].shift(-1).rolling(horizon).max() / df["Close"] - 1.0
        hit = (runup*100.0 >= target_pct).astype(int)
        rows.append({
            "Ticker": t,
            "Signals": int(sig.sum()),
            "HitRate_%": float(100 * (hit[sig].mean() if sig.any() else 0.0)),
            "AvgRunup_%": float(100 * (runup[sig].mean() if sig.any() else 0.0))
        })
    return pd.DataFrame(rows).sort_values("HitRate_%", ascending=False)
