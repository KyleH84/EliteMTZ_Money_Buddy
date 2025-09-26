from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from typing import Dict, List
import random
def top_k_by_score(scores: Dict[int, float], k: int) -> List[int]:
    items = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [n for n,_ in items[:k]]
def uniform_random(pool: List[int], k: int, allow_duplicates: bool = False, seed: int | None = None) -> List[int]:
    rng = random.Random(seed)
    if allow_duplicates:
        return [rng.choice(pool) for _ in range(k)]
    if k >= len(pool):
        return sorted(pool)
    return sorted(rng.sample(pool, k))
