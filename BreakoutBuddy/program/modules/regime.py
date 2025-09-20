from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import pandas as pd
import yfinance as yf
import math

def _pct_rank(s: pd.Series, window:int=252) -> pd.Series:
    return s.rolling(window).apply(lambda x: (x<=x.iloc[-1]).mean(), raw=False)

def _scalar(x):
    if hasattr(x, "iloc"):
        try:
            return float(x.iloc[0])
        except Exception:
            pass
    try:
        return float(x)
    except Exception:
        return float("nan")

def compute_regime() -> dict:
    spy = yf.download("SPY", period="1y", interval="1d", auto_adjust=False, progress=False)
    vix = yf.download("^VIX", period="1y", interval="1d", auto_adjust=False, progress=False)
    regime = {}
    if spy is not None and not spy.empty:
        spy_trend = spy["Close"].pct_change(20, fill_method="pad").tail(1)
        spy_vol = spy["Close"].pct_change(fill_method="pad").rolling(20).std().tail(1)
        regime["spy20d_trend"] = _scalar(spy_trend)
        regime["spy20d_vol"] = _scalar(spy_vol)
        ma200 = spy["Close"].rolling(200).mean()
        slope200 = ma200.diff(5).tail(1)
        val = _scalar(slope200)
        regime["ma200_slope5"] = 0.0 if (val != val or math.isnan(val)) else val
    if vix is not None and not vix.empty:
        vix_pct = _pct_rank(vix["Close"], 252).tail(1)
        regime["vix_percentile"] = _scalar(vix_pct)
    return regime
