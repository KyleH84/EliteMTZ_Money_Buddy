from __future__ import annotations
# Auto-bridge so `utilities.features` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.features import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.features import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.features not found in app utilities') from _e
