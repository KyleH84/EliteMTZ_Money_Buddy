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

DIGITS = list(range(0, 10))

def _load_hist(root_dir: Optional[str], draw_time: Optional[str]) -> pd.DataFrame:
    root = Path(root_dir or ".") / "Data"
    # Try specific files first
    if draw_time:
        p = root / f"cached_pick3_{draw_time.lower()}_data.csv"
        if p.exists():
            try:
                return pd.read_csv(p)
            except Exception:
                pass
    # Fallback
    p = root / "cached_pick3_data.csv"
    if p.exists():
        try:
            return pd.read_csv(p)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def _pos_counts(hist: pd.DataFrame) -> List[pd.Series]:
    cols = [c for c in hist.columns if c.lower() in ("n1","n2","n3","d1","d2","d3")]
    # Map first three number-like columns
    pos = []
    for i in range(3):
        if i < len(cols):
            s = hist[cols[i]].value_counts().reindex(DIGITS, fill_value=0.0)
        else:
            s = pd.Series(0.0, index=DIGITS, dtype=float)
        pos.append(s.astype(float))
    return pos

def _apply_astro(scores: pd.Series, cosmic: Optional[Dict[str, Any]]) -> pd.Series:
    if cosmic is None or not isinstance(scores, pd.Series):
        return scores
    try:
        score = float(((cosmic or {}).get("alignment") or {}).get("score", 0.5))
    except Exception:
        score = 0.5
    gamma = 1.0 + (score - 0.5) * 0.6
    s = scores.copy().astype(float) + 1e-9
    return s.pow(gamma)

def get_pick3_prediction(root_dir: Optional[str] = None, *, draw_time: Optional[str] = None,
                         use_hot_cold: bool = True, use_astro: bool = False,
                         cosmic: Optional[Dict[str, Any]] = None,
                         seed: Optional[int] = None,
                         pinned_digits: Optional[List[Optional[int]]] = None,
                         **_) -> Dict[str, Any]:
    hist = _load_hist(root_dir, draw_time)
    import random
    if seed and seed>0:
        random.seed(int(seed))

    counts = _pos_counts(hist)
    if use_astro and cosmic is not None:
        counts = [ _apply_astro(c, cosmic) for c in counts ]

    digits: List[int] = [None, None, None]
    if pinned_digits:
        for i in range(min(3, len(pinned_digits))):
            try:
                if pinned_digits[i] is not None:
                    v = int(pinned_digits[i])
                    if 0 <= v <= 9:
                        digits[i] = v
            except Exception:
                pass

    for i in range(3):
        if digits[i] is not None:
            continue
        if use_hot_cold and counts[i].sum() > 0:
            pool = counts[i].index.tolist()
            weights = (counts[i].values.astype(float) + 1e-6)
            digits[i] = int(random.choices(pool, weights=weights, k=1)[0])
        else:
            digits[i] = int(random.choice(DIGITS))

    return {"digits": digits, "draw_time": (draw_time or "").lower()}
