from __future__ import annotations
# Auto-bridge so `utilities.ensemble` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.ensemble import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.ensemble import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.ensemble not found in app utilities') from _e
