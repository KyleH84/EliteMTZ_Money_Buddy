from __future__ import annotations
# Auto-bridge so `utilities.performance_tracker` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.performance_tracker import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.performance_tracker import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.performance_tracker not found in app utilities') from _e
