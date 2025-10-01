from __future__ import annotations
# Shim forwarding to BreakoutBuddy.program.utilities.feature_fixups
try:
    from BreakoutBuddy.program.utilities.feature_fixups import *  # type: ignore
except Exception as _e:
    # No-op fallbacks to avoid import crashes
    def ensure_basic_indicators(df): return df
    def fill_feature_gaps(df, spy_ref=None): return df