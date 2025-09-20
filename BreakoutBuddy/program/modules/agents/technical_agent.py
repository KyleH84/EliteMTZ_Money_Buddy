from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


from typing import Optional
import pandas as pd
import numpy as np

from modules.services.ohlcv_cache import get_history

def _rsi(series: pd.Series, period: int = 14) -> float:
    s = series.astype(float).diff()
    up = s.clip(lower=0.0).rolling(period).mean()
    down = (-s.clip(upper=0.0)).rolling(period).mean()
    rs = up / (down + 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return float(rsi.iloc[-1])

class TechnicalAgent:
    """Zero-dependency technical blend: RSI(14) + RVOL(20). Scores ~[-10..+10]."""

    def score(self, symbol: str) -> Optional[float]:
        try:
            df = get_history(symbol, period="6mo", interval="1d")
            if df is None or len(df) < 25: 
                return None
            close = df["Close"]
            vol = df["Volume"]
            rsi = _rsi(close, 14)
            rvol = float(vol.iloc[-1] / (vol.rolling(20).mean().iloc[-1] + 1e-9))

            # Map RSI to -10..+10 (centered at 50)
            rsi_score = (rsi - 50.0) / 5.0  # 10 points per 50±50 => ±10 at 0/100
            rsi_score = max(-10.0, min(10.0, rsi_score))

            # RVOL boost: ±2 at 0.8/1.5 (clamped)
            if rvol >= 1.5:
                rvol_score = 2.0
            elif rvol <= 0.8:
                rvol_score = -2.0
            else:
                rvol_score = (rvol - 1.0) * 4.0  # linear around 1.0

            total = rsi_score + rvol_score
            return max(-10.0, min(10.0, float(total)))
        except Exception:
            return None
