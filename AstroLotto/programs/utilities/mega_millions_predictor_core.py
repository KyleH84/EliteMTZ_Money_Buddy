from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from typing import Any, Dict, List, Optional
import pandas as pd
from pathlib import Path
from .predictor_core_base import top_k_by_score, uniform_random

GAME = {"white_min":1,"white_max":70,"special_min":1,"special_max":25}

def _score_whites(hist: pd.DataFrame) -> pd.Series:
    counts = pd.Series(0.0, index=range(GAME["white_min"], GAME["white_max"]+1), dtype=float)
    if hist is not None and not hist.empty:
        for c in ["n1","n2","n3","n4","n5"]:
            if c in hist.columns:
                counts = counts.add(hist[c].value_counts(), fill_value=0.0)
    return counts

def _score_special(hist: pd.DataFrame) -> pd.Series:
    counts = pd.Series(0.0, index=range(GAME["special_min"], GAME["special_max"]+1), dtype=float)
    if hist is not None and not hist.empty:
        for k in ["mb","mega","special","n6"]:
            if k in hist.columns:
                counts = counts.add(hist[k].value_counts(), fill_value=0.0)
                break
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

def get_mega_millions_prediction(root_dir: Optional[str] = None, *, k_white:int=5, k_special:int=1,
                                 use_hot_cold:bool=True, use_astro:bool=False,
                                 cosmic: Optional[Dict[str, Any]] = None,
                                 allow_duplicates:bool=False,
                                 pinned_whites: Optional[List[int]] = None,
                                 pinned_specials: Optional[List[int]] = None,
                                 seed:Optional[int]=None, **_) -> Dict[str, Any]:
    hist = pd.DataFrame()
    try:
        p = Path(root_dir or ".") / "Data" / "cached_mega_millions_data.csv"
        if p.exists():
            hist = pd.read_csv(p)
    except Exception:
        pass

    import random
    if seed and seed>0:
        random.seed(int(seed))

    whites_all = list(range(GAME["white_min"], GAME["white_max"]+1))
    specials_all = list(range(GAME["special_min"], GAME["special_max"]+1))

    # Start with pins
    w_out: List[int] = []
    s_out: List[int] = []
    if pinned_whites:
        w_out = [n for n in pinned_whites if whites_all[0] <= int(n) <= whites_all[-1]]
        w_out = list(dict.fromkeys(w_out))[:5]
    if pinned_specials:
        s_out = [n for n in pinned_specials if specials_all[0] <= int(n) <= specials_all[-1]]
        s_out = list(dict.fromkeys(s_out))[:1]

    k_w = 5 - len(w_out)
    k_s = 1 - len(s_out)

    if use_hot_cold:
        w_scores = _score_whites(hist)
        s_scores = _score_special(hist)
        if use_astro and cosmic:
            w_scores = _apply_astro(w_scores, cosmic)
            s_scores = _apply_astro(s_scores, cosmic)
        w_fill = top_k_by_score(w_scores.drop(index=w_out, errors="ignore"), max(0, k_w))
        s_fill = top_k_by_score(s_scores.drop(index=s_out, errors="ignore"), max(0, k_s))
    else:
        w_fill = uniform_random([n for n in whites_all if n not in w_out], max(0, k_w), allow_duplicates=False)
        s_fill = uniform_random([n for n in specials_all if n not in s_out], max(0, k_s), allow_duplicates=True)

    whites = sorted(list(dict.fromkeys(w_out + w_fill)))[:5]
    special = (s_out + s_fill)[:1]
    return {"white": whites, "special": special}
