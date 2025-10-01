from __future__ import annotations
# Auto-bridge so `utilities.planetary_alignment` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.planetary_alignment import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.planetary_alignment import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.planetary_alignment not found in app utilities') from _e
