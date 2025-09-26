from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


# Compatibility shim: older code imports this name.
# We forward to temporal_autotune if present, otherwise provide safe fallbacks.

try:
    from temporal_autotune import (
        TemporalControls,
        apply_temporal_to_weights,
        apply_temporal_to_vector,
    )
except Exception:
    class TemporalControls:
        def __init__(self, **kwargs):
            self.params = dict(kwargs)

    def apply_temporal_to_weights(weights, *args, **kwargs):
        return weights

    def apply_temporal_to_vector(vec, *args, **kwargs):
        return vec
