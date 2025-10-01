from __future__ import annotations
# Auto-bridge so `utilities.caching` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.caching import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.caching import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.caching not found in app utilities') from _e
