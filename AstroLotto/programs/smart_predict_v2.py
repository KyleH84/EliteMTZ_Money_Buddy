# Program/utilities/smart_predict_v2.py
from __future__ import annotations
from typing import Dict, List, Any, Tuple
import random
import pandas as pd
from .smart_features import WHITE_RANGES, SPECIAL_RANGES, detect_white_columns, long_short_blend, gap_overdue_bonus, compute_special_scores
from .wrs import weighted_sample_without_replacement as wrs_wor
from .pmi import pmi_pairs
from .diversity import select_diverse

def _weighted_choice(keys: List[int], weights: List[float]) -> int:
    tot = sum(weights) or 1.0
    r = random.random() * tot; c = 0.0
    for x, w in zip(keys, weights):
        c += w
        if r <= c: return x
    return keys[-1]

def _sample_whites(game: str, base_scores: Dict[int,float], k: int, use_wrs: bool, pair_bonus: Dict[Tuple[int,int],float]) -> List[int]:
    lo, hi, _ = WHITE_RANGES[game]
    domain = list(range(lo, hi+1))
    weights = [max(1e-9, float(base_scores.get(i, 0.0))) for i in domain]
    if use_wrs: return wrs_wor(domain, weights, k)
    chosen: List[int] = []
    w = {i: weights[idx] for idx,i in enumerate(domain)}
    for _ in range(k):
        if chosen and pair_bonus:
            for i in domain:
                if i in chosen: continue
                bump = 1.0
                for c in chosen:
                    a,b = (c,i) if c < i else (i,c)
                    if (a,b) in pair_bonus: bump *= (1.0 + 0.2 * pair_bonus[(a,b)])
                w[i] *= bump
        pool = [i for i in domain if i not in chosen]
        ws = [w[i] for i in pool]
        x = _weighted_choice(pool, ws)
        chosen.append(x)
    return sorted(chosen)

def _choose_special(game: str, df: pd.DataFrame, model: Dict[str,Any]) -> int | None:
    lo_hi = SPECIAL_RANGES.get(game)
    if not lo_hi: return None
    lo, hi = lo_hi
    keys = list(range(lo, hi+1))
    scores = (model.get("special_scores") if isinstance(model, dict) else None) or compute_special_scores(df, game)
    weights = [max(1e-9, float(scores.get(i, 0.0))) for i in keys]
    return _weighted_choice(keys, weights)

def predict_sets_v2(game: str, df: pd.DataFrame, model: Dict[str,Any]|None, n_sets: int = 5,
                    short_days: int = 30, alpha: float = 0.3, gap_strength: float = 0.2,
                    n_sims: int = 5000, chaos_pct: float = 0.05,
                    use_wrs: bool = True, use_pmi: bool = True, diversity_target: float = 0.5) -> List[Dict[str,Any]]:
    lo, hi, k = WHITE_RANGES[game]
    whites = detect_white_columns(df)
    base = long_short_blend(df, game, short_days=short_days, alpha=alpha)
    gap = gap_overdue_bonus(df, game, strength=gap_strength)
    base_scores = {i: max(1e-9, base.get(i, 0.0) * gap.get(i, 1.0)) for i in range(lo, hi+1)}
    try:
        if isinstance(model, dict) and "scores" in model:
            _bias = model.get("scores") or {}
            for _k in list(range(lo, hi+1)):
                b = float(_bias.get(str(_k), _bias.get(_k, 0.0)) or 0.0)
                base_scores[_k] = max(1e-12, base_scores.get(_k, 1e-12) * (1.0 + b))
    except Exception:
        pass

    pairs = pmi_pairs(df, whites) if use_pmi and whites else {}
    from collections import Counter
    tally = Counter()
    for _ in range(int(n_sims)):
        bs = base_scores.copy()
        if chaos_pct > 0:
            import random as _r
            n_pert = max(1, int((hi - lo + 1) * chaos_pct))
            for i in _r.sample(list(range(lo, hi+1)), n_pert):
                bs[i] *= _r.uniform(1.05, 1.3)
        pick = tuple(_sample_whites(game, bs, k, use_wrs, pairs))
        tally[pick] += 1
    ranked = [list(t[0]) for t in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))]
    selected = select_diverse(ranked, n_sets, target=float(diversity_target)) if diversity_target > 0 else ranked[:n_sets]
    out = []
    for w in selected:
        spec = _choose_special(game, df, model or {}) if game in ("powerball","megamillions","luckyforlife") else ""
        out.append({"white": w, "special": spec, "notes": "smart-v2"})
    return out