from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

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
    # Ensure all expected features exist and fill missing with safe defaults
    # If some core features are missing entirely, try to recompute from fresh snapshot.
    try:
        needed = [c for c in EXPECTED_FEATURES if c not in merged.columns]
        if needed:
            # Attempt to pull fresh enriched rows and merge missing cols
            try:
                _fix = data_mod.pull_enriched_snapshot(list(merged['Ticker'].dropna().astype(str).unique()))
                if not _fix.empty:
                    use_cols = [c for c in _fix.columns if c in needed or c == 'Ticker']
                    merged = merged.merge(_fix[use_cols], on='Ticker', how='left', suffixes=('', '_fresh'))
            except Exception:
                pass
        # Now guarantee presence with defaults
        defaults = {
            "Close": 0.0, "ChangePct": 0.0, "RSI2": 50.0, "RSI4": 50.0,
            "ConnorsRSI": 50.0, "RelSPY": 0.0, "RVOL": 1.0, "ATR": 0.0,
            "PctFrom200d": 0.0, "SqueezeHint": 0.0,
            "P_up": 0.55, "CrowdRisk": 0.0, "AgentsScore": None, "AgentsConf": None,
        }
        for _c, _d in defaults.items():
            if _c not in merged.columns:
                merged[_c] = _d
        # Fill NaNs with defaults for display stability
        for _c, _d in defaults.items():
            merged[_c] = pd.to_numeric(merged[_c], errors='coerce') if isinstance(_d, (int,float)) else merged[_c]
            merged[_c] = merged[_c].fillna(_d)
    except Exception:
        pass

    return merged
