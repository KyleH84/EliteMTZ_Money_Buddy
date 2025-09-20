from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


from typing import List, Dict, Any
import random
import pandas as pd
from .smart_features import WHITE_RANGES, SPECIAL_RANGES, detect_white_columns
try:
    from .smart_features import long_short_blend, gap_overdue_bonus
except Exception:
    long_short_blend = None
    gap_overdue_bonus = None

def _blend_hotcold_weights(df: pd.DataFrame, game: str) -> Dict[int, float]:
    # Use long/short blend and gap bonus if available; else uniform
    try:
        base = long_short_blend(df, game, short_days=30, alpha=0.3) if long_short_blend else {}
        gap = gap_overdue_bonus(df, game, strength=0.2) if gap_overdue_bonus else {}
    except Exception:
        base, gap = {}, {}
    lo, hi, _ = WHITE_RANGES.get(game, (1, 69, 5))
    w = {}
    for i in range(lo, hi+1):
        b = float(base.get(i, 1.0))
        g = float(gap.get(i, 1.0)) if gap else 1.0
        w[i] = max(1e-9, b * g)
    return w


def _weighted_sample_unique(pop, weights, k):
    if len(pop) <= k: return sorted(pop)
    total = sum(max(0.0,w) for w in weights) or 1.0
    pool = list(zip(pop, [max(0.0,w)/total for w in weights]))
    picks=[]
    for _ in range(k):
        r=random.random(); acc=0.0
        for i,(n,w) in enumerate(pool):
            acc+=w
            if r<=acc or i==len(pool)-1:
                picks.append(n)
                pool.pop(i)
                rem=sum(w for _,w in pool) or 1.0
                pool=[(nn, ww/rem) for nn,ww in pool]
                break
    return sorted(picks)

def _freq_weights_from_df(df: pd.DataFrame, game: str) -> Dict[int,float]:
    lo, hi, _ = WHITE_RANGES.get(game, (1,69,5))
    if df is None or df.empty: return {i:1.0 for i in range(lo,hi+1)}
    whites = detect_white_columns(df)
    if not whites: return {i:1.0 for i in range(lo,hi+1)}
    series = [pd.to_numeric(df[c], errors="coerce") for c in whites]
    vals = pd.concat(series, axis=0).dropna().astype(int)
    counts = vals.value_counts().to_dict()
    if long_short_blend:
        try:
            bl = long_short_blend(df, game, short_days=30, alpha=0.25)
            for n,v in bl.items(): counts[n]=counts.get(n,0)+0.2*v
        except Exception: pass
    if gap_overdue_bonus:
        try:
            gb = gap_overdue_bonus(df, game, strength=0.15)
            for n,v in gb.items(): counts[n]=counts.get(n,0)+0.15*(v-1.0)
        except Exception: pass
    return {i: 0.5+float(counts.get(i,0)) for i in range(lo,hi+1)}

def predict_frequency_fallback(game: str, df: pd.DataFrame, model: Dict[str,Any], n_picks: int = 3) -> List[Dict[str,Any]]:
    game = (game or "").lower().strip()
    lo,hi,k = WHITE_RANGES.get(game, (1,69,5))
    pop = list(range(lo,hi+1))
    base = _freq_weights_from_df(df, game)
    model_scores = {}
    if isinstance(model, dict):
        model_scores = model.get("scores") or model.get("white_scores") or {}
    for i in pop:
        try:
            base[i] = max(0.0, float(base.get(i,1.0))) * (1.0 + 0.15*float(model_scores.get(str(i), model_scores.get(i, 0.0))))
        except Exception:
            pass
    weights = [base[i] for i in pop]
    out=[]
    for _ in range(max(1,int(n_picks or 1))):
        white = _weighted_sample_unique(pop, weights, k)
        pick = {"white": white, "notes": "fallback"}
        if game in SPECIAL_RANGES:
            slo,shi = SPECIAL_RANGES[game]
            # Try special frequency if present
            special=None
            if isinstance(df, pd.DataFrame) and not df.empty:
                for c in df.columns:
                    if str(c).lower() in ("special","powerball","mega_ball","megaball","lucky_ball","bonus"):
                        s = pd.to_numeric(df[c], errors="coerce").dropna().astype(int)
                        if not s.empty:
                            sc = s.value_counts().to_dict()
                            spop=list(range(slo,shi+1))
                            sweights=[0.5+float(sc.get(i,0)) for i in spop]
                            special=_weighted_sample_unique(spop, sweights, 1)[0]
                            break
            if special is None:
                special = random.randint(slo,shi)
            pick["special"]=special
        else:
            pick["special"]=""
        out.append(pick)
    return out
