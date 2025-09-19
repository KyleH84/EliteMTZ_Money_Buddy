
from __future__ import annotations
from pathlib import Path
from typing import Iterable, Optional, Dict, Tuple, List

import numpy as np
import pandas as pd

from modules.features import load_features

# Resolve BreakoutBuddy/Data/breakoutbuddy.duckdb relative to this file
DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "Data" / "breakoutbuddy.duckdb"

# Canonical feature set expected by most agent trainers
CANONICAL_COLS: List[str] = [
    "Close","ChangePct","RelSPY","RVOL","RSI4","ConnorRSI",
    "ATR","ADX","SqueezeOn","SqueezeHint","GapPct"
]

# Common aliases coming from different pipelines
ALIASES: Dict[str, str] = {
    "relspy": "RelSPY",
    "rel_spy": "RelSPY",
    "rvol": "RVOL",
    "rsi4": "RSI4",
    "crsi": "ConnorRSI",
    "connorsrsi": "ConnorRSI",
    "adx14": "ADX",
    "atr14": "ATR",
    "squeeze_on": "SqueezeOn",
    "squeeze": "SqueezeOn",
    "squeezehint": "SqueezeHint",
    "gap": "GapPct",
    "gap_pct": "GapPct",
    "change": "ChangePct",
    "change_pct": "ChangePct",
}

def _canonicalize(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known aliases and keep only [Ticker] + CANONICAL_COLS that exist."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Ticker"] + CANONICAL_COLS)
    cols = {c: ALIASES.get(c.lower(), c) for c in df.columns}
    df = df.rename(columns=cols)
    keep = [c for c in CANONICAL_COLS if c in df.columns]
    out = df[["Ticker"] + keep].copy() if "Ticker" in df.columns else df[keep].copy()
    # Types & cleaning
    for c in keep:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if "SqueezeOn" in out.columns:
        out["SqueezeOn"] = out["SqueezeOn"].fillna(0).astype(int).clip(0, 1)
    return out

def _zscore(x: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    mu = np.nanmean(x, axis=0, keepdims=True)
    sd = np.nanstd(x, axis=0, keepdims=True)
    sd = np.where(sd < eps, 1.0, sd)
    z = (x - mu) / sd
    return np.nan_to_num(z, nan=0.0, posinf=0.0, neginf=0.0)

def _make_priors(df: pd.DataFrame) -> Dict[str, float]:
    """Very light heuristic prior P(up) in [0,1] used by some agent ensembles."""
    pri = {}
    if df is None or df.empty or "Ticker" not in df.columns:
        return pri
    rsi = df.get("RSI4")
    rel = df.get("RelSPY")
    base = 0.5 + (np.tanh((np.nan_to_num(rel, nan=0.0) or 0) / 0.1) * 0.1 if rel is not None else 0)
    # If RSI present, nudge away from extremes
    if rsi is not None:
        r = np.nan_to_num(rsi.values, nan=50.0)
        r_adj = -((r - 50.0) / 60.0)  # hot => -; cold => +
        base = 0.5 + np.clip(r_adj, -0.25, 0.25)
    tickers = df["Ticker"].astype(str).tolist()
    vals = np.clip(np.asarray(base).reshape(-1).astype(float), 0.05, 0.95)
    for t, p in zip(tickers, vals):
        pri[t] = float(p)
    return pri

def load_features_for_agents(
    db_path: Path | str = DEFAULT_DB_PATH,
    tickers: Optional[Iterable[str]] = None,
    latest: bool = True,
    scale: bool = True,
) -> Dict[str, object]:
    """Convenience loader for agent training/inference.

    Returns a dict with:
      - frame: canonicalized feature DataFrame (Ticker + columns)
      - X: numpy feature matrix (scaled if scale=True)
      - cols: list of feature column names (order of X)
      - tickers: list of tickers in the same order as rows in X
      - priors: dict[ticker] -> prior win probability in [0,1]
    """
    df = load_features(db_path, tickers=tickers, latest=latest)
    df = _canonicalize(df)
    if df.empty:
        return {"frame": df, "X": np.zeros((0, 0)), "cols": [], "tickers": [], "priors": {}}
    feat_cols = [c for c in CANONICAL_COLS if c in df.columns]
    X = df[feat_cols].to_numpy(dtype=float)
    if scale and X.size:
        X = _zscore(X)
    tickers_list = df["Ticker"].astype(str).tolist() if "Ticker" in df.columns else [f"row{i}" for i in range(len(df))]
    priors = _make_priors(df)
    return {"frame": df, "X": X, "cols": feat_cols, "tickers": tickers_list, "priors": priors}

def join_features_with(
    left: pd.DataFrame,
    right: pd.DataFrame,
    how: str = "left",
) -> pd.DataFrame:
    """Merge helper on Ticker for post-processing (e.g., attach agent outputs)."""
    if left is None or left.empty:
        return right
    if right is None or right.empty:
        return left
    if "Ticker" not in left.columns or "Ticker" not in right.columns:
        return left
    return left.merge(right, on="Ticker", how=how)
