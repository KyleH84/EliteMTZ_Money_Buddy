from __future__ import annotations
# Auto-bridge so `utilities.retrocausal_feedback` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.retrocausal_feedback import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.retrocausal_feedback import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.retrocausal_feedback not found in app utilities') from _e
