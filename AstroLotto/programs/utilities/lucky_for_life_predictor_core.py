from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path
from .predictor_core_base import top_k_by_score, uniform_random

GAME = {"white_min": 1, "white_max": 48, "special_min": 1, "special_max": 18}

def _hist_counts(hist: pd.DataFrame, cols: List[str], rng: range) -> pd.Series:
    counts = pd.Series(0.0, index=list(rng), dtype=float)
    if hist is not None and not hist.empty:
        for c in cols:
            if c in hist.columns:
                counts = counts.add(hist[c].value_counts(), fill_value=0.0)
    return counts

def _apply_astro(scores: pd.Series, cosmic: Optional[Dict[str, Any]]) -> pd.Series:
    if not isinstance(scores, pd.Series) or cosmic is None:
        return scores
    try:
        score = float(((cosmic or {}).get("alignment") or {}).get("score", 0.5))
    except Exception:
        score = 0.5
    gamma = 1.0 + (score - 0.5) * 0.6
    s = scores.copy().astype(float) + 1e-9
    return s.pow(gamma)

def get_lucky_for_life_prediction(root_dir: Optional[str] = None, *, k_white:int=5, k_special:int=1,
                                  use_hot_cold:bool=True, use_astro:bool=False,
                                  cosmic: Optional[Dict[str, Any]] = None,
                                  allow_duplicates:bool=False, pinned_whites: Optional[List[int]] = None,
                                  pinned_specials: Optional[List[int]] = None,
                                  seed:Optional[int]=None, **_) -> Dict[str, Any]:
    hist = pd.DataFrame()
    try:
        p = Path(root_dir or ".") / "Data" / "cached_lucky_for_life_data.csv"
        if p.exists():
            hist = pd.read_csv(p)
    except Exception:
        pass

    import random
    if seed and seed>0:
        random.seed(int(seed))

    whites_all = list(range(GAME["white_min"], GAME["white_max"]+1))
    specials_all = list(range(GAME["special_min"], GAME["special_max"]+1))

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
        w_counts = _hist_counts(hist, ["n1","n2","n3","n4","n5"], range(GAME["white_min"], GAME["white_max"]+1))
        s_counts = _hist_counts(hist, ["lb","lucky","special","n6"], range(GAME["special_min"], GAME["special_max"]+1))
        if use_astro:
            w_counts = _apply_astro(w_counts, cosmic)
            s_counts = _apply_astro(s_counts, cosmic)
        # weighted choice without replacement for whites, single draw for special
        def choose(counts: pd.Series, already: List[int], k: int) -> List[int]:
            if k <= 0: return []
            s = counts.drop(index=already, errors="ignore")
            s = s + (s.eq(0) * 1e-6)
            pool = s.index.tolist()
            weights = s.values.astype(float)
            out: List[int] = []
            import random, numpy as np
            for _ in range(min(k, len(pool))):
                total = float(weights.sum())
                if total <= 0:
                    remaining = [n for n in pool if n not in out]
                    out += uniform_random(remaining, k-len(out), allow_duplicates=False)
                    break
                pick = random.choices(pool, weights=weights, k=1)[0]
                out.append(int(pick))
                idx = pool.index(pick)
                pool.pop(idx); weights = np.delete(weights, idx)
            return out
        w_fill = choose(w_counts, w_out, k_w)
        if k_s > 0:
            s_fill = choose(s_counts, s_out, k_s)
        else:
            s_fill = []
    else:
        w_fill = uniform_random([n for n in whites_all if n not in w_out], k_w, allow_duplicates=False)
        s_fill = uniform_random([n for n in specials_all if n not in s_out], k_s, allow_duplicates=True)

    whites = sorted(list(dict.fromkeys(w_out + w_fill)))[:5]
    special = (s_out + s_fill)[:1]
    return {"white": whites, "special": special}
