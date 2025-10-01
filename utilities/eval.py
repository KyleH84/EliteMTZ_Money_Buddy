from __future__ import annotations
# Auto-bridge so `utilities.eval` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.eval import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.eval import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.eval not found in app utilities') from _e
