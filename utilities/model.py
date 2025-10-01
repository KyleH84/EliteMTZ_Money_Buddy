from __future__ import annotations
# Auto-bridge so `utilities.model` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.model import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.model import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.model not found in app utilities') from _e
