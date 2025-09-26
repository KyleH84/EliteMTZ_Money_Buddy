from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


# temporal_agent.py
# A tiny, dependency-light "temporal helper" you can drop into any project.
# Baseline model + optional Kozyrev-style time-energy correction.
# Author: ChatGPT (Chad) for Kyle
# License: MIT

from dataclasses import dataclass
from typing import Callable, Any, Dict, List, Optional, Tuple, Union, Sequence

# Physical constant (exact by definition)
PLANCK_H = 6.62607015e-34  # J*s

# Type aliases for readability
# Baseline model returns the observable at time t_next
BaselineFn = Callable[[float, Dict[str, Any], Dict[str, Any]], Union[float, Sequence[float]]]
# Sensitivity returns d(observable)/dt at time t_next (same shape as the model output)
SensitivityFn = Callable[[float, Dict[str, Any], Dict[str, Any]], Union[float, Sequence[float]]]

@dataclass
class KozyrevConfig:
    enabled: bool = False
    kappa: float = 0.0            # units: s/J (to be calibrated from data)
    dt_ref: float = 1.0           # reference Δt0 in seconds
    default_dt_window: float = 1.0  # fallback Δt in seconds

def _is_sequence(x: Any) -> bool:
    return isinstance(x, (list, tuple))

def _apply_elementwise(y: Union[float, Sequence[float]],
                       dy: Union[float, Sequence[float]]) -> Union[float, List[float]]:
    """
    Adds dy to y, elementwise if they are sequences. Returns same container style (list for sequence).
    """
    if _is_sequence(y) and _is_sequence(dy):
        if len(y) != len(dy):
            raise ValueError("Shape mismatch: y and dy must have the same length.")
        return [float(a) + float(b) for a, b in zip(y, dy)]
    elif _is_sequence(y) and not _is_sequence(dy):
        # broadcast scalar dy to sequence y
        return [float(a) + float(dy) for a in y]  # type: ignore[arg-type]
    elif (not _is_sequence(y)) and _is_sequence(dy):
        raise ValueError("Shape mismatch: y is scalar but dy is a sequence.")
    else:
        return float(y) + float(dy)  # both scalars

class TemporalAgent:
    """
    Predict the next observable using a baseline model and an optional Kozyrev-style correction.

    You provide:
      - model_fn(t, state, ctx) -> observable
      - sensitivity_fn(t, state, ctx) -> d(observable)/dt near t

    Kozyrev layer uses: Δt_K = κ * h * (1/Δt - 1/Δt0)
    Final: y_final ≈ y_base + (d y / d t) * Δt_K

    If kozyrev.enabled == False or kappa == 0, you get pure baseline.
    """
    def __init__(self,
                 model_fn: BaselineFn,
                 sensitivity_fn: SensitivityFn,
                 kozyrev: Optional[KozyrevConfig] = None):
        self.model_fn = model_fn
        self.sensitivity_fn = sensitivity_fn
        self.kozyrev = kozyrev or KozyrevConfig()

    def predict(self,
                t_next: float,
                state: Dict[str, Any],
                context: Optional[Dict[str, Any]] = None,
                dt_window: Optional[float] = None) -> Dict[str, Any]:
        """
        t_next: target time (seconds). UNIX epoch or any monotonic seconds base.
        state: arbitrary dict of model parameters/state
        context: optional dict for extra inputs/features
        dt_window: Δt (seconds) — your system's effective temporal resolution/horizon

        Returns dict with baseline and corrected predictions:
          {
            "y_base": ...,
            "y_final": ...,
            "delta_y_K": ...,
            "dt_K": float,
            "Et": float,
            "Et0": float
          }
        """
        ctx = context or {}

        # 1) Baseline prediction
        y_base = self.model_fn(t_next, state, ctx)

        # 2) Kozyrev correction
        if not self.kozyrev.enabled or self.kozyrev.kappa == 0.0:
            return {
                "y_base": y_base,
                "y_final": y_base,
                "delta_y_K": 0.0 if not _is_sequence(y_base) else [0.0] * len(y_base),  # type: ignore[arg-type]
                "dt_K": 0.0,
                "Et": None,
                "Et0": None
            }

        dt0 = max(1e-12, float(self.kozyrev.dt_ref))
        dt = float(dt_window) if dt_window is not None else float(self.kozyrev.default_dt_window)
        dt = max(1e-12, dt)

        # Time-energy densities Et = h / Δt
        Et = PLANCK_H / dt
        Et0 = PLANCK_H / dt0

        # Δt_K = κ * (Et - Et0) = κ * h * (1/Δt - 1/Δt0)
        dt_K = self.kozyrev.kappa * (Et - Et0)

        # Local sensitivity ∂y/∂t
        dydt = self.sensitivity_fn(t_next, state, ctx)

        # First-order correction
        if _is_sequence(dydt):
            delta_y_K = [float(s) * float(dt_K) for s in dydt]  # type: ignore[arg-type]
        else:
            delta_y_K = float(dydt) * float(dt_K)  # scalar

        y_final = _apply_elementwise(y_base, delta_y_K)

        return {
            "y_base": y_base,
            "y_final": y_final,
            "delta_y_K": delta_y_K,
            "dt_K": dt_K,
            "Et": Et,
            "Et0": Et0
        }

    # ---------- Calibration helpers (scalar target) ----------
    def estimate_kappa(self,
                       samples: List[Tuple[float, float, Dict[str, Any], Dict[str, Any], Optional[float]]],
                       dt_ref: Optional[float] = None) -> float:
        """
        Estimate κ from data for a SCALAR observable via simple linear regression.

        Each sample: (t_next, y_obs, state, context, dt_window)
        Uses residual_i ≈ (∂y/∂t)_i * κ * h * (1/Δt_i - 1/Δt0)
        => residual_i = phi_i * κ, where phi_i = (∂y/∂t)_i * h * (1/Δt_i - 1/Δt0)
        κ_hat = sum(phi_i * residual_i) / sum(phi_i^2)
        """
        dt0 = float(dt_ref) if dt_ref is not None else self.kozyrev.dt_ref
        dt0 = max(1e-12, dt0)

        num = 0.0
        den = 0.0
        for (t_next, y_obs, state, context, dt_window) in samples:
            ctx = context or {}
            y_base = self.model_fn(t_next, state, ctx)
            if _is_sequence(y_base):
                raise ValueError("estimate_kappa: This scalar fitter does not support vector outputs.")
            resid = float(y_obs) - float(y_base)

            dt = float(dt_window) if dt_window is not None else self.kozyrev.default_dt_window
            dt = max(1e-12, dt)
            X = PLANCK_H * (1.0/dt - 1.0/dt0)
            S = self.sensitivity_fn(t_next, state, ctx)
            if _is_sequence(S):
                raise ValueError("estimate_kappa: Sensitivity must be scalar for this fitter.")
            phi = float(S) * float(X)
            num += phi * resid
            den += phi * phi

        kappa_hat = 0.0 if den == 0.0 else num / den
        self.kozyrev.kappa = kappa_hat
        if dt_ref is not None:
            self.kozyrev.dt_ref = dt_ref
        self.kozyrev.enabled = True
        return kappa_hat

# --------- Simple example baselines you can reuse or replace ---------
def linear_model(t_next: float, state: Dict[str, Any], ctx: Dict[str, Any]) -> float:
    """
    y(t) = y0 + v * (t - t0)
    state: { 't0': float, 'y0': float, 'v': float }
    """
    t0 = state['t0']; y0 = state['y0']; v = state['v']
    return float(y0) + float(v) * (float(t_next) - float(t0))

def linear_sensitivity(t_next: float, state: Dict[str, Any], ctx: Dict[str, Any]) -> float:
    """
    ∂y/∂t = v
    """
    return float(state['v'])

# Optional: finite-difference sensitivity helper if you don't have an analytic derivative.
def finite_diff_sensitivity(model_fn: BaselineFn,
                            eps: float = 1e-3) -> SensitivityFn:
    """
    Returns a sensitivity function that estimates ∂y/∂t via symmetric finite differences.
    Supports scalar outputs only (to keep it dependency-free).
    """
    def _s(t_next: float, state: Dict[str, Any], ctx: Dict[str, Any]) -> float:
        y1 = model_fn(t_next + eps, state, ctx)
        y0 = model_fn(t_next - eps, state, ctx)
        if _is_sequence(y1) or _is_sequence(y0):
            raise ValueError("finite_diff_sensitivity: Only scalar outputs supported. Provide your own vector sensitivity.")
        return (float(y1) - float(y0)) / (2.0 * eps)
    return _s
