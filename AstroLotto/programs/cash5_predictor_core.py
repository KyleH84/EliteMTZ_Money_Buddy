from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path
from .predictor_core_base import top_k_by_score, uniform_random

GAME = {"white_min": 1, "white_max": 32}

def _hist_counts(hist: pd.DataFrame, col_names: List[str], bounds: range) -> pd.Series:
    counts = pd.Series(0.0, index=list(bounds), dtype=float)
    if hist is not None and not hist.empty:
        for c in col_names:
            if c in hist.columns:
                counts = counts.add(hist[c].value_counts(), fill_value=0.0)
    return counts

def _apply_astro(scores: pd.Series, cosmic: Optional[Dict[str, Any]]) -> pd.Series:
    if not isinstance(scores, pd.Series) or cosmic is None:
        return scores
    # Use alignment score if available, else neutral 0.5
    try:
        score = float(((cosmic or {}).get("alignment") or {}).get("score", 0.5))
    except Exception:
        score = 0.5
    # Gamma 0.7..1.3 centered at 1.0
    gamma = 1.0 + (score - 0.5) * 0.6
    s = scores.copy().astype(float) + 1e-9
    return s.pow(gamma)

def get_cash5_prediction(root_dir: Optional[str] = None, *, k_white:int=5,
                         use_hot_cold:bool=True, use_astro:bool=False,
                         cosmic: Optional[Dict[str, Any]] = None,
                         allow_duplicates:bool=False, pinned_whites: Optional[List[int]] = None,
                         seed:Optional[int]=None, **_) -> Dict[str, Any]:
    hist = pd.DataFrame()
    try:
        p = Path(root_dir or ".") / "Data" / "cached_cash5_data.csv"
        if p.exists():
            hist = pd.read_csv(p)
    except Exception:
        pass

    import random
    if seed and seed>0:
        random.seed(int(seed))

    whites_all = list(range(GAME["white_min"], GAME["white_max"]+1))
    out: List[int] = []
    if pinned_whites:
        out = [n for n in pinned_whites if whites_all[0] <= int(n) <= whites_all[-1]]
        out = list(dict.fromkeys(out))[:5]

    k = 5 - len(out)
    if k <= 0:
        return {"white": sorted(out)[:5]}

    if use_hot_cold:
        counts = _hist_counts(hist, ["n1","n2","n3","n4","n5"], range(GAME["white_min"], GAME["white_max"]+1))
        if use_astro:
            counts = _apply_astro(counts, cosmic)
        # Sample without replacement proportional to counts (add small epsilon to avoid zeros)
        s = counts.drop(index=out, errors="ignore")
        s = s + (s.eq(0) * 1e-6)  # avoid all zeros
        # Weighted choice without replacement: iterative
        pool = s.index.tolist()
        weights = s.values.astype(float)
        chosen: List[int] = []
        for _ in range(min(k, len(pool))):
            total = float(weights.sum())
            if total <= 0:
                # fallback
                remaining = [n for n in pool if n not in chosen]
                chosen += uniform_random(remaining, k-len(chosen), allow_duplicates=False)
                break
            pick = random.choices(pool, weights=weights, k=1)[0]
            chosen.append(int(pick))
            # remove picked
            idx = pool.index(pick)
            pool.pop(idx); weights = np.delete(weights, idx)
        fill = chosen
    else:
        fill = uniform_random([n for n in whites_all if n not in out], k, allow_duplicates=False)

    whites = sorted(list(dict.fromkeys(out + fill)))[:5]
    return {"white": whites}
