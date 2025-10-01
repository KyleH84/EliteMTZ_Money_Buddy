from __future__ import annotations
# Auto-bridge so `utilities.alignment` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.alignment import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.alignment import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.alignment not found in app utilities') from _e
