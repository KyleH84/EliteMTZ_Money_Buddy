# Program/utilities/diversity.py
from __future__ import annotations
from typing import List

def _set_distance(a: List[int], b: List[int]) -> float:
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    uni = len(sa | sb)
    if uni == 0: return 0.0
    return 1.0 - (inter / uni)

def select_diverse(candidates: List[List[int]], m: int, target: float = 0.5) -> List[List[int]]:
    if not candidates: return []
    m = min(m, len(candidates))
    chosen = [candidates[0]]
    remaining = candidates[1:]
    while len(chosen) < m and remaining:
        best = None; best_d = -1.0
        for cand in remaining:
            d = min(_set_distance(cand, s) for s in chosen)
            if d > best_d: best_d, best = d, cand
        chosen.append(best); remaining.remove(best)
        if best_d >= target and len(chosen) >= m: break
    return chosen