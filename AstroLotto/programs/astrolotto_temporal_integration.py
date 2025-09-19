
# astrolotto_temporal_integration.py
# Drop-in utilities to apply the TemporalAgent to AstroLotto's white-ball weights.
# Designed to avoid invasive edits to your app_main.py.
# License: MIT

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional, Tuple, List
import numpy as np

from temporal_agent import TemporalAgent, KozyrevConfig

@dataclass
class TemporalControls:
    enabled: bool = False
    kappa: float = 0.0       # s/J
    dt_ref: float = 86400.0  # seconds
    dt_window: float = 86400.0  # seconds
    eps_days: float = 1.0    # finite-diff step in days

def vector_fd_sensitivity(model_fn: Callable[[float, Dict[str, Any], Dict[str, Any]], List[float]],
                          eps_sec: float):
    """Return a sensitivity function that estimates dW/dt via symmetric finite differences.
    model_fn must return a list/array of weights for the white-ball domain at epoch (seconds).
    """
    def _s(t_next: float, state: Dict[str, Any], ctx: Dict[str, Any]):
        Wp = np.asarray(model_fn(t_next + eps_sec, state, ctx), dtype=float)
        Wm = np.asarray(model_fn(t_next - eps_sec, state, ctx), dtype=float)
        if Wp.shape != Wm.shape:
            raise ValueError("FD sensitivity: shape mismatch.")
        return ((Wp - Wm) / (2.0 * eps_sec)).tolist()
    return _s

def apply_temporal_to_weights(get_weights_for_epoch: Callable[[float], List[float]],
                              controls: TemporalControls,
                              next_draw_epoch: float,
                              state: Optional[Dict[str, Any]] = None,
                              ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Apply Kozyrev correction to white-ball weight vector.

    get_weights_for_epoch: function(epoch_seconds) -> list[float] (already normalized is fine)
    controls: TemporalControls (toggle and parameters)
    next_draw_epoch: target epoch in seconds (e.g., your next draw time)
    state/ctx: optional dicts passed through (not required)

    Returns dict with:
      - W_base: baseline weights (list[float])
      - W_final: corrected + renormalized weights (list[float])
      - diagnostics: {Et, Et0, dt_K, delta_W, ...}
    """
    state = state or {}
    ctx = ctx or {}
    W_base = np.asarray(get_weights_for_epoch(next_draw_epoch), dtype=float)
    # Normalize
    s = W_base.sum()
    if s > 0:
        W_base = W_base / s

    if not controls.enabled or controls.kappa == 0.0:
        return {
            "W_base": W_base.tolist(),
            "W_final": W_base.tolist(),
            "diagnostics": {"Et": None, "Et0": None, "dt_K": 0.0, "delta_W": [0.0]*len(W_base)}
        }

    # Build a tiny model_fn wrapper and sensitivity
    def _model_W(t_next: float, _state: Dict[str, Any], _ctx: Dict[str, Any]):
        return get_weights_for_epoch(t_next)

    eps_sec = float(controls.eps_days) * 86400.0
    sens_fn = vector_fd_sensitivity(_model_W, eps_sec=eps_sec)

    agent = TemporalAgent(
        model_fn=_model_W,
        sensitivity_fn=sens_fn,
        kozyrev=KozyrevConfig(
            enabled=True,
            kappa=float(controls.kappa),
            dt_ref=float(controls.dt_ref),
            default_dt_window=float(controls.dt_window),
        )
    )

    out = agent.predict(next_draw_epoch, state, ctx, dt_window=float(controls.dt_window))
    W_final = np.asarray(out["y_final"], dtype=float)
    # Renormalize
    s = W_final.sum()
    if s > 0:
        W_final = W_final / s

    # delta vector for debugging
    if isinstance(out["delta_y_K"], list):
        delta_vec = out["delta_y_K"]
    else:
        # scalar sensitivity would be unusual here; broadcast for completeness
        delta_vec = [float(out["delta_y_K"])] * len(W_final)

    return {
        "W_base": W_base.tolist(),
        "W_final": W_final.tolist(),
        "diagnostics": {
            "Et": out["Et"], "Et0": out["Et0"], "dt_K": out["dt_K"],
            "delta_W": [float(x) for x in delta_vec]
        }
    }


def apply_temporal_to_vector(get_vector_for_epoch,  # Callable[[float], List[float]]
                             controls: TemporalControls,
                             next_epoch: float,
                             state: Optional[Dict[str, Any]] = None,
                             ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generic version for any probability vector (e.g., special ball).
    """
    state = state or {}
    ctx = ctx or {}
    V_base = np.asarray(get_vector_for_epoch(next_epoch), dtype=float)
    s = V_base.sum()
    if s > 0:
        V_base = V_base / s

    if not controls.enabled or controls.kappa == 0.0:
        return {
            "V_base": V_base.tolist(),
            "V_final": V_base.tolist(),
            "diagnostics": {"Et": None, "Et0": None, "dt_K": 0.0, "delta_V": [0.0]*len(V_base)}
        }

    def _model_V(t_next: float, _state: Dict[str, Any], _ctx: Dict[str, Any]):
        return get_vector_for_epoch(t_next)

    eps_sec = float(controls.eps_days) * 86400.0
    sens_fn = vector_fd_sensitivity(_model_V, eps_sec=eps_sec)

    agent = TemporalAgent(
        model_fn=_model_V,
        sensitivity_fn=sens_fn,
        kozyrev=KozyrevConfig(
            enabled=True,
            kappa=float(controls.kappa),
            dt_ref=float(controls.dt_ref),
            default_dt_window=float(controls.dt_window),
        )
    )

    out = agent.predict(next_epoch, state, ctx, dt_window=float(controls.dt_window))
    V_final = np.asarray(out["y_final"], dtype=float)
    s = V_final.sum()
    if s > 0:
        V_final = V_final / s

    if isinstance(out["delta_y_K"], list):
        delta_vec = out["delta_y_K"]
    else:
        delta_vec = [float(out["delta_y_K"])] * len(V_final)

    return {
        "V_base": V_base.tolist(),
        "V_final": V_final.tolist(),
        "diagnostics": {
            "Et": out["Et"], "Et0": out["Et0"], "dt_K": out["dt_K"],
            "delta_V": [float(x) for x in delta_vec]
        }
    }
