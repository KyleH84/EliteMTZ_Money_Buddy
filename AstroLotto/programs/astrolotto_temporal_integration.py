from __future__ import annotations

# This module exists only to keep older imports working.
# It forwards to temporal_autotune, or provides safe fallbacks.

try:
    from temporal_autotune import (
        TemporalControls,
        apply_temporal_to_weights,
        apply_temporal_to_vector,
    )
except Exception as e:
    # Safe fallbacks if temporal_autotune isn't available
    class TemporalControls:
        def __init__(self, **kwargs):
            self.params = kwargs
    def apply_temporal_to_weights(weights, *args, **kwargs):
        return weights
    def apply_temporal_to_vector(vec, *args, **kwargs):
        return vec
