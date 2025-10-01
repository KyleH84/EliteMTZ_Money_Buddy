from __future__ import annotations
# Auto-bridge so `utilities.archetypal_engine` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.archetypal_engine import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.archetypal_engine import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.archetypal_engine not found in app utilities') from _e
