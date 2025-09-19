from __future__ import annotations
from typing import List, Optional
import pandas as pd
from modules import data as data_mod

# Feature names we try to ensure are present after enrichment.
EXPECTED_FEATURES = [
    "Ticker","Close","ChangePct","RSI2","RSI4","ConnorsRSI","RelSPY","RVOL","ATR","PctFrom200d","SqueezeHint",
    "P_up","CrowdRisk","AgentsScore","AgentsConf"
]

def prices_for(tickers: List[str]) -> pd.DataFrame:
    """
    Convenience: fetch normalized OHLCV for a set of tickers.
    Delegates to modules.data.pull_enriched_snapshot then selects price columns when available.
    """
    df = data_mod.pull_enriched_snapshot(tickers)
    keep = [c for c in ["Ticker","Open","High","Low","Close","Volume","ChangePct"] if c in df.columns]
    return df[keep] if keep else df

def enrich_features(tickers: List[str], base_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Compute or refresh enriched snapshot rows for the given tickers.
    If base_df is provided, merge freshly computed columns on 'Ticker' and prefer fresh values.
    """
    fresh = data_mod.pull_enriched_snapshot(tickers)
    if base_df is None or base_df.empty:
        return fresh
    key = "Ticker" if "Ticker" in base_df.columns else None
    if not key:
        return fresh
    # Drop any overlapping feature columns in base_df then left-join fresh.
    overlap = [c for c in fresh.columns if c != key and c in base_df.columns]
    merged = base_df.drop(columns=overlap, errors="ignore").merge(fresh, on=key, how="left")
    return merged
