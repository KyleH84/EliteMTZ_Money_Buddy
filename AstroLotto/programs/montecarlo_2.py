from __future__ import annotations
from typing import Dict, List, Tuple, Any
import random
import pandas as pd
from .smart_features import WHITE_RANGES, SPECIAL_RANGES, long_short_blend, gap_overdue_bonus

def _weighted_choice(items: List[int], weights: List[float]) -> int:
    total = sum(weights) + 1e-12
    r = random.random() * total
    c = 0.0
    for x, w in zip(items, weights):
        c += w
        if r <= c:
            return x
    return items[-1]

def _pair_bonus(df: pd.DataFrame, game: str, top_k_pairs: int = 30) -> Dict[tuple,float]:
    """Lightweight pair bias just for 5/6-number games. Not used for pick3."""
    from collections import Counter
    whites = [c for c in df.columns if c.lower().startswith("white")] or [f"n{i}" for i in range(1,7) if f"n{i}" in df.columns]
    if not whites:
        return {}
    cnt = Counter()
    for _, row in df.iterrows():
        try:
            nums = sorted(int(row[c]) for c in whites)
        except Exception:
            continue
        for i in range(len(nums)):
            for j in range(i+1, len(nums)):
                cnt[(nums[i], nums[j])] += 1
    top = dict(cnt.most_common(top_k_pairs))
    if top:
        m = max(top.values())
        for k in list(top.keys()):
            top[k] = top[k]/m
    return top

def sample_set(game: str, base_scores: Dict[int,float], df: pd.DataFrame, pair_bonus: Dict[tuple,float], chaos_pct: float = 0.0, allow_repeats: bool = False) -> List[int]:
    lo, hi, k = WHITE_RANGES[game]
    chosen: List[int] = []
    pool = list(range(lo, hi+1))
    weights = {i: max(1e-9, float(base_scores.get(i, 0.0))) for i in pool}
    if chaos_pct > 0:
        chaos_n = max(1, int(len(pool) * chaos_pct))
        for i in random.sample(pool, chaos_n):
            weights[i] *= random.uniform(1.1, 1.5)
    for _ in range(k):
        if chosen and pair_bonus and not allow_repeats:
            for i in pool:
                if i in chosen: 
                    continue
                bump = 1.0
                for c in chosen:
                    a,b = (c,i) if c < i else (i,c)
                    if (a,b) in pair_bonus:
                        bump *= (1.0 + 0.15 * pair_bonus[(a,b)])
                weights[i] *= bump
        items = pool if allow_repeats else [i for i in pool if i not in chosen]
        wlist = [weights[i] for i in items]
        x = _weighted_choice(items, wlist)
        chosen.append(x)
    if allow_repeats:
        return chosen  # keep order for pick3
    return sorted(chosen)

def monte_carlo_picks(game: str, df: pd.DataFrame, n_sets: int = 5, n_sims: int = 5000, short_days: int = 30, alpha: float = 0.3, gap_strength: float = 0.2, chaos_pct: float = 0.05) -> List[List[int]]:
    lo, hi, k = WHITE_RANGES[game]
    base = long_short_blend(df, game, short_days=short_days, alpha=alpha)
    gap = gap_overdue_bonus(df, game, strength=gap_strength)
    base_scores = {i: max(1e-9, base.get(i, 0.0) * gap.get(i, 1.0)) for i in range(lo, hi+1)}
    if game == "pick3":
        # Ordered with replacement
        tally: Dict[tuple,int] = {}
        for _ in range(max(500, n_sims//10)):
            s = tuple(sample_set(game, base_scores, df, pair_bonus={}, chaos_pct=chaos_pct, allow_repeats=True))
            tally[s] = tally.get(s, 0) + 1
        ranked = sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))
        return [list(t[0]) for t in ranked[:n_sets]]
    pair_bonus = _pair_bonus(df, game)
    tally: Dict[tuple,int] = {}
    for _ in range(n_sims):
        s = tuple(sample_set(game, base_scores, df, pair_bonus=pair_bonus, chaos_pct=chaos_pct, allow_repeats=False))
        tally[s] = tally.get(s, 0) + 1
    ranked = sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))
    return [list(t[0]) for t in ranked[:n_sets]]

def choose_special(game: str, df: pd.DataFrame, model: Dict[str,Any] | None) -> int | None:
    lo_hi = SPECIAL_RANGES.get(game)
    if not lo_hi:
        return None
    lo, hi = lo_hi
    # prefer model special_scores; fall back to compute from df
    scores = None
    if isinstance(model, dict):
        scores = model.get("special_scores")
    if not scores:
        # compute from df
        col = None
        for c in df.columns:
            lc = c.lower()
            if game == "powerball" and lc == "powerball": col = c; break
            if game == "megamillions" and lc in ("mega_ball","megaball","mega"): col = c; break
            if game == "luckyforlife" and lc in ("lucky_ball","luckyball","lucky"): col = c; break
            if lc in ("special","bonus"): col = c; break
        if col:
            s = pd.to_numeric(df[col], errors="coerce").dropna().astype(int)
            vc = s.value_counts().to_dict()
            total = sum(vc.values()) or 1
            scores = {i: vc.get(i, 0) / total for i in range(lo, hi+1)}
        else:
            scores = {i: 1.0 for i in range(lo, hi+1)}
    keys = list(range(lo, hi+1))
    w = [max(1e-9, float(scores.get(i, 0.0))) for i in keys]
    return _weighted_choice(keys, w)
