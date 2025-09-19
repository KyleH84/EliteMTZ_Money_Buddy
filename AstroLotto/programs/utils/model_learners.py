# Dependency-free learners with optional ML detection
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict
import numpy as np, pandas as pd, json
from pathlib import Path

@dataclass
class PickSet:
    picks: List[List[int]]
    info: Dict[str, str]

class FrequencyEWMA:
    def __init__(self, max_number: int, decay: float = 0.98):
        self.max_n = max_number
        self.decay = float(decay)
        self.w = np.ones(self.max_n, dtype=float)
    def update_from_draws(self, arr: np.ndarray) -> None:
        for row in arr:
            self.w *= self.decay
            for n in set(int(x) for x in row if 1 <= int(x) <= self.max_n):
                self.w[n-1] += (1.0 - self.decay)
    def suggest(self, k: int, n_sets: int = 5, rng: Optional[np.random.Generator] = None) -> PickSet:
        rng = rng or np.random.default_rng()
        probs = self.w / self.w.sum()
        picks = []
        for _ in range(n_sets):
            sel = rng.choice(np.arange(1, self.max_n+1), size=k, replace=False if k<=self.max_n else True, p=probs)
            sel.sort(); picks.append(sel.tolist())
        return PickSet(picks=picks, info={"model":"FrequencyEWMA","decay":f"{self.decay}"} )

class PairCooccurrenceBoost:
    def __init__(self, max_number: int, co_mat: Optional[np.ndarray] = None, boost: float = 0.15):
        self.max_n = max_number; self.boost = float(boost)
        self.co = co_mat if co_mat is not None else np.zeros((max_number, max_number), dtype=float)
    @staticmethod
    def from_draws(max_number: int, arr: np.ndarray, boost: float = 0.15):
        co = np.zeros((max_number, max_number), dtype=float)
        for row in arr:
            s = sorted(set(int(x) for x in row if 1 <= int(x) <= max_number))
            for i in range(len(s)):
                for j in range(i+1, len(s)):
                    a,b = s[i]-1, s[j]-1
                    co[a,b] += 1; co[b,a] += 1
        row_sums = co.sum(axis=1, keepdims=True); row_sums[row_sums==0] = 1.0
        co = co / row_sums
        return PairCooccurrenceBoost(max_number, co, boost)
    def suggest_with_seed(self, seed_set: List[int], k: int, n_sets: int = 5, rng: Optional[np.random.Generator] = None) -> PickSet:
        rng = rng or np.random.default_rng()
        base = np.ones(self.max_n, dtype=float) / self.max_n
        picks = []
        for _ in range(n_sets):
            probs = base.copy()
            for s in seed_set:
                if 1 <= s <= self.max_n: probs += self.boost * self.co[s-1]
            probs /= probs.sum()
            sel = rng.choice(np.arange(1, self.max_n+1), size=k, replace=False if k<=self.max_n else True, p=probs)
            sel.sort(); picks.append(sel.tolist())
        return PickSet(picks=picks, info={"model":"PairCooccurrenceBoost","boost":f"{self.boost}","seed":str(seed_set)} )

def optional_ml_available() -> str:
    try:
        import autogluon.tabular as ag  # noqa
        return "AutoGluon"
    except Exception:
        pass
    try:
        from sklearn.ensemble import RandomForestClassifier  # noqa
        return "scikit-learn"
    except Exception:
        pass
    return "none"

def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(data, indent=2))
def load_json(path: Path) -> dict:
    if path.exists():
        try: return json.loads(path.read_text())
        except Exception: return {}
    return {}
