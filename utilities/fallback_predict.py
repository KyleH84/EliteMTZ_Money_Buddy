from __future__ import annotations
# Neutral shim so imports like `from utilities.fallback_predict import fallback_predict`
# resolve to AstroLotto's local implementation without crossing into BreakoutBuddy.
try:
    from AstroLotto.programs.utilities.fallback_predict import fallback_predict  # type: ignore
except Exception as _e:  # very unlikely; keep app alive
    def fallback_predict(*args, **kwargs):  # type: ignore
        raise ImportError("fallback_predict unavailable: " + str(_e))
