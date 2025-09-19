# Program/utilities/wrs.py
from __future__ import annotations
from typing import List
import math, random

def weighted_sample_without_replacement(items: List[int], weights: List[float], k: int) -> List[int]:
    """
    Efraimidis-Spirakis weighted sampling without replacement.
    Returns k distinct items sampled proportionally to weights.
    """
    k = min(k, len(items))
    keys = []
    for x, w in zip(items, weights):
        w = max(1e-12, float(w))
        u = random.random()
        keys.append((math.pow(u, 1.0 / w), x))
    keys.sort(reverse=True)
    return sorted([x for _, x in keys[:k]])