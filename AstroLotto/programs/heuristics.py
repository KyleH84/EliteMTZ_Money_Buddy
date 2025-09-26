from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/heuristics.py
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
import numpy as np

@dataclass
class HeuristicParams:
    exclude_last_n: int = 3            # reject exact matches with any of last N draws
    max_overlap_with_last_n: int = 4   # reject if overlap >= this with any of last N draws
    enforce_odd_even_balance: bool = True
    cold_boost: str = "balanced"       # "none" | "balanced" | "cold-boost"

def _last_n(history: pd.DataFrame, n: int, white_cols: List[str]) -> List[List[int]]:
    if history is None or history.empty or n <= 0:
        return []
    out = []
    for _, r in history.tail(n).iterrows():
        try:
            out.append(sorted(int(r[c]) for c in white_cols if c in history.columns))
        except Exception:
            continue
    return out

def _overlap(a: List[int], b: List[int]) -> int:
    return len(set(a) & set(b))

def _passes_recent(pick: List[int], recents: List[List[int]], n_exact: int, max_ov: int) -> bool:
    if not recents:
        return True
    for h in recents:
        if n_exact > 0 and sorted(pick) == sorted(h):
            return False
        if max_ov >= 0 and _overlap(pick, h) >= max_ov:
            return False
    return True

def _passes_odd_even(pick: List[int], want_balance: bool) -> bool:
    if not want_balance:
        return True
    k = len(pick)
    odd = sum(1 for x in pick if x % 2)
    lo, hi = k // 2, (k + 1) // 2     # e.g., 5 -> allow 2 or 3 odds
    return lo <= odd <= hi

def _reweight(weights: Dict[int, float], mode: str) -> Dict[int, float]:
    keys = sorted(int(k) for k in weights.keys())
    arr = np.array([float(weights[k]) for k in keys], dtype=float) + 1e-6
    if mode == "balanced":
        arr = np.power(arr, 0.5)  # squash extremes
    elif mode == "cold-boost":
        norm = (arr - arr.min()) / (arr.max() - arr.min() + 1e-9)
        arr = 0.5 * arr + 0.5 * (1.0 - norm + 1e-6)
    arr = arr / arr.sum()
    return {int(k): float(v) for k, v in zip(keys, arr)}

def _sample_unique(scores: Dict[int, float], k: int, rng: np.random.Generator) -> List[int]:
    items = sorted(scores.items(), key=lambda x: int(x[0]))
    nums = np.array([int(i) for i,_ in items], dtype=int)
    wts  = np.array([max(0.0, float(s)) for _,s in items], dtype=float) + 1e-6
    idx = rng.choice(len(nums), size=min(k, len(nums)), replace=False, p=wts / wts.sum())
    return sorted(nums[idx].tolist())

def select_with_heuristics(
    cached_df: pd.DataFrame,
    white_cols: List[str],
    white_scores: Dict[int, float],
    white_count: int,
    n_picks: int,
    params: HeuristicParams
) -> List[List[int]]:
    rng = np.random.default_rng()
    scores = _reweight(white_scores, params.cold_boost) if params.cold_boost != "none" else {int(k): float(v) for k,v in white_scores.items()}
    recents = _last_n(cached_df, params.exclude_last_n, white_cols)

    picks: List[List[int]] = []
    attempts = 0
    while len(picks) < n_picks and attempts < 2000:
        attempts += 1
        cand = _sample_unique(scores, white_count, rng)
        if not _passes_odd_even(cand, params.enforce_odd_even_balance):
            continue
        if not _passes_recent(cand, recents, params.exclude_last_n, params.max_overlap_with_last_n):
            continue
        picks.append(cand)
    return picks
