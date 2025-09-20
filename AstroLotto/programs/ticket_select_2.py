from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/ticket_select.py
import numpy as np, random

def _rules(game: str):
    g = (game or "").lower()
    if g.startswith("power"): return 5,1,69,1,26
    if g.startswith("mega"): return 5,1,70,1,25
    if "colorado" in g: return 6,1,40,None,None
    if "cash5" in g: return 5,1,32,None,None
    if "lucky" in g: return 5,1,48,1,18
    if "pick3" in g: return 3,0,9,None,None
    return 5,1,70,1,26

def _sample_without_replacement(rng, low, high, k, probs=None):
    pool = list(range(low, high+1))
    if probs is None:
        return sorted(rng.sample(pool, k))
    out=[]
    p = np.array(probs, dtype=float).copy()
    p = p / p.sum()
    for _ in range(k):
        idx = rng.choices(range(len(pool)), weights=p, k=1)[0]
        out.append(pool[idx])
        pool.pop(idx); p = np.delete(p, idx)
        if p.sum() > 0: p = p / p.sum()
        if len(pool)==0: break
    return sorted(out)

def select_tickets(prob_table, game: str, n_tickets: int=1, strategy: str="balanced", seed=None):
    k_white,wmin,wmax,smin,smax = _rules(game)
    rng = random.Random(seed)
    whites_probs = prob_table["white"]
    special_probs = prob_table.get("special", None)
    out=[]
    for _ in range(int(max(1,n_tickets))):
        if strategy=="coverage":
            wp = 1.0 - whites_probs
            wp = wp / wp.sum()
        elif strategy=="ev":
            wp = whites_probs
        else:
            wp = whites_probs**0.8
            wp = wp / wp.sum()
        whites = _sample_without_replacement(rng, wmin, wmax, k_white, probs=wp)
        if smin is not None and special_probs is not None:
            sp = (special_probs**0.9); sp = sp / sp.sum()
            special_pool = list(range(smin, smax+1))
            special = rng.choices(special_pool, weights=sp, k=1)[0]
        else:
            special = None
        out.append({"white": whites, "special": special})
    return out

def enhance_from_raw_predictions(items, prob_table, game: str, n_tickets: int=1, strategy: str="balanced", seed=None):
    k_white,wmin,wmax,smin,smax = _rules(game)
    rng = random.Random(seed)
    whites_probs = prob_table["white"]
    special_probs = prob_table.get("special", None)
    out=[]
    for it in items[:max(1,int(n_tickets))]:
        whites = sorted([n for n in (it.get("white") or []) if isinstance(n,int) and wmin<=n<=wmax][:k_white])
        if len(whites) < k_white:
            add = select_tickets(prob_table, game, 1, strategy=strategy, seed=seed)[0]["white"]
            for n in add:
                if n not in whites and len(whites)<k_white:
                    whites.append(n)
            whites = sorted(whites[:k_white])
        special = it.get("special")
        if smin is not None and (special is None or not (smin<=int(special)<=smax)) and special_probs is not None:
            special_pool = list(range(smin, smax+1))
            special = rng.choices(special_pool, weights=special_probs, k=1)[0]
        out.append({"white": whites, "special": special})
    return out
