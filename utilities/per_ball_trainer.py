from __future__ import annotations
# Auto-bridge so `utilities.per_ball_trainer` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.per_ball_trainer import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.per_ball_trainer import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.per_ball_trainer not found in app utilities') from _e
