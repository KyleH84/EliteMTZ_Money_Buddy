from __future__ import annotations
# Auto-bridge so `utilities.config` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.config import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.config import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.config not found in app utilities') from _e
