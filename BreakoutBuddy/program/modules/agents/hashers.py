
from __future__ import annotations
import pandas as pd, hashlib, numpy as np

def hist_hash(df: pd.DataFrame, cols=None, last_n: int = 120) -> str:
    """Stable sha1 of last_n bars of selected columns."""
    if df is None or df.empty:
        return ""
    if cols is None:
        cols = [c for c in ["Date","Open","High","Low","Close","Adj Close","Volume"] if c in df.columns]
    take = df.tail(last_n)[cols].copy()
    for c in take.columns:
        take[c] = pd.to_numeric(take[c], errors="coerce")
    b = take.to_numpy().tobytes()
    return hashlib.sha1(b).hexdigest()
