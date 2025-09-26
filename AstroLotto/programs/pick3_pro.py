from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from typing import Dict, List
import pandas as pd
from collections import Counter
def _digits_for_row(row, cols: List[str]) -> List[int]:
    out = []
    for c in cols:
        try:
            v = int(row[c])
            if 0 <= v <= 9:
                out.append(v)
        except Exception:
            out.append(0)
    return out
def per_position_distributions(df: pd.DataFrame, cols: List[str]) -> List[Dict[int,float]]:
    outs = []
    for i, c in enumerate(cols):
        s = pd.to_numeric(df[c], errors="coerce").dropna().astype(int)
        cnt = Counter({d:1 for d in range(10)})
        for v in s:
            if 0 <= v <= 9:
                cnt[v] += 1
        total = sum(cnt.values())
        outs.append({d: cnt[d]/total for d in range(10)})
    return outs
def sample_pick3_set(df: pd.DataFrame, cols: List[str]) -> List[int]:
    import random
    dists = per_position_distributions(df, cols)
    out = []
    for pos in range(3):
        digits = list(range(10))
        weights = [dists[pos].get(d, 0.1) for d in digits]
        s = sum(weights) or 1.0
        weights = [w/s for w in weights]
        r = random.random()
        c = 0.0
        for d, w in zip(digits, weights):
            c += w
            if r <= c:
                out.append(d); break
    return out
