
from __future__ import annotations
from typing import Optional
import duckdb
import pandas as pd

from .cache import _conn

def _latest_agentcalib(con=None) -> pd.DataFrame:
    con = con or _conn()
    try:
        df = con.execute("""
            SELECT Date, BinLow, BinHigh, Count, HitRate
            FROM AgentCalib
            WHERE Metric='AgentsScore'
            QUALIFY row_number() OVER (ORDER BY Date DESC) = 1
        """).fetchdf()
        return df
    except Exception:
        return pd.DataFrame()

def get_agents_multiplier_cap(default_cap: float = 1.15) -> float:
    """Compute an adaptive cap for the Agents multiplier.
    Returns a value in [1.10, 1.18] where higher = more trust in agents.
    Based on sample size (Count) and calibration MAE vs diagonal.
    """
    df = _latest_agentcalib()
    if df is None or df.empty:
        return float(default_cap)
    df = df.copy()
    try:
        df['Mid'] = (df['BinLow'].astype(float) + df['BinHigh'].astype(float)) / 2.0
        df['AbsErr'] = (df['HitRate'].astype(float) - df['Mid']).abs()
        n = float(df['Count'].astype(float).sum())
        if n <= 0:
            return float(default_cap)
        mae = float((df['AbsErr'] * df['Count']).sum() / n)
        # Confidence from size & error: more rows, lower error → higher confidence
        size_term = min(1.0, n / 1000.0)              # saturates at 1000 samples
        error_term = max(0.0, 1.0 - min(1.0, mae / 0.08))  # 0 error →1, 8% abs error →0
        conf_score = size_term * error_term           # 0..1
        cap = 1.10 + 0.08 * conf_score
        return float(max(1.10, min(1.18, cap)))
    except Exception:
        return float(default_cap)
