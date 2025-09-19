from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd
from pathlib import Path
from .predictor_core_base import top_k_by_score, uniform_random

# Default range; can be overridden if history shows a different max
GAME = {"white_min":1,"white_max":40}

def _score_whites(hist: pd.DataFrame) -> pd.Series:
    maxv = GAME["white_max"]
    if hist is not None and not hist.empty:
        cols = [c for c in hist.columns if c.lower() in ("n1","n2","n3","n4","n5","n6")]
        if cols:
            maxv = int(pd.to_numeric(hist[cols], errors="coerce").max().max() or maxv)
    counts = pd.Series(0.0, index=range(GAME["white_min"], maxv+1), dtype=float)
    if hist is not None and not hist.empty:
        for c in ["n1","n2","n3","n4","n5","n6"]:
            if c in hist.columns:
                counts = counts.add(hist[c].value_counts(), fill_value=0.0)
    return counts

def _alignment_gamma(cosmic: Optional[Dict[str, Any]]) -> float:
    try:
        score = float(((cosmic or {}).get("alignment") or {}).get("score", 0.5))
    except Exception:
        score = 0.5
    return 1.0 + (score - 0.5) * 0.6

def _apply_astro(scores: pd.Series, cosmic: Optional[Dict[str, Any]]) -> pd.Series:
    if cosmic is None or scores is None:
        return scores
    gamma = _alignment_gamma(cosmic)
    s = scores.copy().astype(float) + 1e-9
    return s.pow(gamma)

def get_colorado_lottery_prediction(root_dir: Optional[str] = None, *, k_white:int=6,
                                    use_hot_cold:bool=True, use_astro:bool=False,
                                    cosmic: Optional[Dict[str, Any]] = None,
                                    allow_duplicates:bool=False,
                                    pinned_whites: Optional[List[int]] = None,
                                    seed:Optional[int]=None, **_) -> Dict[str, Any]:
    hist = pd.DataFrame()
    try:
        p = Path(root_dir or ".") / "Data" / "cached_colorado_lottery_data.csv"
        if p.exists():
            hist = pd.read_csv(p)
    except Exception:
        pass

    import random
    if seed and seed>0:
        random.seed(int(seed))

    # Determine bounds
    w_scores = _score_whites(hist)
    if use_hot_cold and use_astro and cosmic is not None:
        w_scores = _apply_astro(w_scores, cosmic)
    whites_all = list(map(int, w_scores.index))

    # Apply pins
    out: List[int] = []
    if pinned_whites:
        out = [n for n in pinned_whites if whites_all[0] <= int(n) <= whites_all[-1]]
        out = list(dict.fromkeys(out))[:6]

    k = 6 - len(out)
    if use_hot_cold:
        fill = top_k_by_score(w_scores.drop(index=out, errors="ignore"), max(0, k))
    else:
        fill = uniform_random([n for n in whites_all if n not in out], max(0, k), allow_duplicates=False)

    whites = sorted(list(dict.fromkeys(out + fill)))[:6]
    return {"white": whites}
