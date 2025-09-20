
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import random
from typing import Dict, Any, List
from .state import PickSet

class MonteCarloAgent:
    def __init__(self, sampler_fn):
        self.sampler_fn = sampler_fn

    def sample(self, model_probs: Dict[str, Any], mode: str, seed: int | None) -> List[PickSet]:
        temp = 0.85
        pool = 64
        if mode == "rainbow":
            temp, pool = 1.25, 256
        elif mode == "oracle_forward":
            temp, pool = 1.05, 128
        elif mode == "most_likely":
            temp, pool = 0.75, 48

        if seed is None:
            seed = random.randint(1, 2_147_483_647)
        raw = self.sampler_fn(model_probs, seed=seed, temperature=temp, pool_size=pool)
        picks = []
        for r in raw:
            if isinstance(r, dict):
                picks.append(PickSet(white=r.get("white", []), special=r.get("special", 0), meta=r.get("meta", {})))
            else:
                white, special = r
                picks.append(PickSet(white=list(white), special=int(special), meta={}))
        return picks
