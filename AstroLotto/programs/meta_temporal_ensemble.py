from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


# meta_temporal_ensemble.py
# General meta-ensemble that queries N members, applies temporal correction per member,
# then combines into one prediction. Works for scalar or vector outputs.
# License: MIT

from dataclasses import dataclass
from typing import Dict, Any, Callable, List, Optional, Tuple, Union, Sequence
import math

from temporal_agent import TemporalAgent, KozyrevConfig

Numeric = Union[float, Sequence[float]]

@dataclass
class Member:
    name: str
    weight: float  # ensemble weight (can be learned or static)
    model_fn: Callable[[float, Dict[str, Any], Dict[str, Any]], Numeric]
    sensitivity_fn: Callable[[float, Dict[str, Any], Dict[str, Any]], Numeric]
    kozyrev: KozyrevConfig

class MetaTemporalEnsemble:
    """
    General meta-ensemble that queries N members, applies temporal correction per member,
    then combines into one prediction.
    - Scalar outputs: returns a single float
    - Vector outputs: returns a list[float] normalized to a distribution if positive
    """
    def __init__(self, members: List[Member], combine: str = "weighted"):
        """
        combine:
          - "weighted": weighted average (scalar) or weighted sum then normalize (vector)
          - "softmax":  temperature-softmax (scalar only)
        """
        self.members = members
        self.combine = combine

    def predict(self, t_next: float, state: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None,
                dt_window: Optional[float] = None, temperature: float = 1.0) -> Dict[str, Any]:
        ctx = ctx or {}
        contribs = []
        outputs: List[Numeric] = []
        weights: List[float] = []

        # 1) collect member predictions (baseline + kozyrev-adjusted)
        for m in self.members:
            agent = TemporalAgent(m.model_fn, m.sensitivity_fn, m.kozyrev)
            res = agent.predict(t_next, state, ctx, dt_window=dt_window)
            outputs.append(res["y_final"])
            weights.append(m.weight)
            contribs.append({
                "member": m.name,
                "weight": m.weight,
                "y_base": res["y_base"],
                "y_final": res["y_final"],
                "delta_y_K": res["delta_y_K"],
                "dt_K": res["dt_K"],
                "Et": res["Et"],
                "Et0": res["Et0"],
                "kozyrev_enabled": m.kozyrev.enabled and (m.kozyrev.kappa != 0.0)
            })

        # 2) fuse
        final = self._combine(outputs, weights, mode=self.combine, temperature=temperature)

        return {
            "final": final,
            "members": contribs,
            "combine": self.combine,
            "temperature": temperature
        }

    # ---------- helpers ----------
    def _combine(self, outputs: List[Numeric], weights: List[float], mode: str, temperature: float) -> Numeric:
        if isinstance(outputs[0], (list, tuple)):
            # vector combine (e.g., lottery weights)
            L = len(outputs[0])
            wsum = max(1e-12, sum(weights))
            acc = [0.0]*L
            for out, w in zip(outputs, weights):
                if len(out) != L:
                    raise ValueError("All vector outputs must have same length.")
                for i in range(L):
                    acc[i] += float(w) * float(out[i])
            # normalize to a proper distribution if positive
            tot = sum(max(0.0, x) for x in acc)
            if tot > 0:
                acc = [max(0.0, x)/tot for x in acc]
            else:
                # fallback to weight-normalized average
                acc = [x/wsum for x in acc]
            return acc
        else:
            # scalar combine
            xs = [float(x) for x in outputs]
            if mode == "weighted":
                wsum = max(1e-12, sum(weights))
                return sum(w * x for w, x in zip(weights, xs)) / wsum
            elif mode == "softmax":
                # temperature-softmax over member outputs, return expectation under softmax
                t = max(1e-6, temperature)
                exps = [math.exp(x/t) for x in xs]
                Z = max(1e-12, sum(exps))
                probs = [e/Z for e in exps]
                return sum(p*x for p, x in zip(probs, xs))
            else:
                raise ValueError("Unknown combine mode.")
