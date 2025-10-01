from __future__ import annotations
# Auto-bridge so `utilities.oracle_data` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.oracle_data import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.oracle_data import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.oracle_data not found in app utilities') from _e
