from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/heuristics_pick3.py
from dataclasses import dataclass
from typing import List, Dict
import numpy as np
import pandas as pd

@dataclass
class Pick3Params:
    exclude_last_n: int = 3        # avoid exact repeats of last N draws
    odd_even_balance: bool = False # optional: 1 or 2 odds allowed (not strict)

def _detect_cols(df: pd.DataFrame) -> List[str]:
    # Try common schemas: white1..white3 or n1..n3 or d1..d3
    for cand in [["white1","white2","white3"], ["n1","n2","n3"], ["d1","d2","d3"]]:
        if all(c in df.columns for c in cand):
            return cand
    # Fallback: first three int-like columns except draw_date
    ints = [c for c in df.columns if c.lower()!="draw_date"]
    return ints[:3]

def _recent_exact(df: pd.DataFrame, n: int, cols: List[str]) -> List[List[int]]:
    if df is None or df.empty or n <= 0:
        return []
    out = []
    for _, r in df.tail(n).iterrows():
        try:
            out.append([int(r[c]) for c in cols])
        except Exception:
            continue
    return out

def _build_position_weights(df: pd.DataFrame, cols: List[str]) -> List[np.ndarray]:
    weights = []
    for c in cols:
        counts = np.zeros(10, dtype=float)  # digits 0..9
        for v in df[c].dropna().astype(int).tolist():
            if 0 <= v <= 9:
                counts[v] += 1.0
        counts = counts + 1e-6
        weights.append(counts / counts.sum())
    return weights

def _passes_odd_even(digits: List[int]) -> bool:
    odd = sum(1 for d in digits if d % 2 == 1)
    return 1 <= odd <= 2  # heuristic: avoid all odd or all even by default

def generate_pick3(
    df: pd.DataFrame,
    n_picks: int = 3,
    params: Pick3Params = Pick3Params()
) -> List[List[int]]:
    cols = _detect_cols(df)
    if len(cols) != 3:
        return []
    recents = _recent_exact(df, params.exclude_last_n, cols)
    w = _build_position_weights(df, cols)
    rng = np.random.default_rng()
    out: List[List[int]] = []
    tries = 0
    while len(out) < n_picks and tries < 2000:
        tries += 1
        digits = [int(rng.choice(10, p=wpos)) for wpos in w]
        if digits in recents and params.exclude_last_n > 0:
            continue
        if params.odd_even_balance and not _passes_odd_even(digits):
            continue
        out.append(digits)
    return out
