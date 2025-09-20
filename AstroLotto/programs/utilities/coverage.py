from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


from typing import List
from .diversity import select_diverse

def coverage_sets(candidates: List[List[int]], n_sets: int, strength: float = 0.5) -> List[List[int]]:
    # strength in [0,1] maps to diversity target [0.5, 0.8]
    target = 0.5 + 0.3 * max(0.0, min(1.0, float(strength)))
    return select_diverse(candidates, n_sets, target=target)
