from __future__ import annotations
# Auto-bridge so `utilities.smart_features` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.smart_features import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.smart_features import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.smart_features not found in app utilities') from _e
