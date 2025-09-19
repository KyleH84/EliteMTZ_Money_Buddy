from __future__ import annotations
import pandas as pd
import numpy as np
import yfinance as yf

def compute_labels_for_symbol(ticker: str, horizon: int = 5, target_pct: float = 3.0) -> pd.DataFrame:
    df = yf.download(ticker, period="2y", interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename_axis("Date").reset_index()
    runup = df["Close"].shift(-1).rolling(horizon).max() / df["Close"] - 1.0
    df["RetFwdMax_%"] = runup * 100.0
    df[f"Hit_+{int(target_pct)}in{horizon}d"] = (df["RetFwdMax_%"] >= target_pct).astype(int)
    return df[["Date","Open","High","Low","Close","Volume","RetFwdMax_%",f"Hit_+{int(target_pct)}in{horizon}d"]]
