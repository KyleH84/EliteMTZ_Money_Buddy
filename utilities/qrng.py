from __future__ import annotations
# Auto-bridge so `utilities.qrng` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.qrng import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.qrng import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.qrng not found in app utilities') from _e
