from __future__ import annotations
# Auto-bridge so `utilities.oracle_engine` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.oracle_engine import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.oracle_engine import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.oracle_engine not found in app utilities') from _e
