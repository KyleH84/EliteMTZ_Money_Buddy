from __future__ import annotations
# Auto-bridge so `utilities.sacred_geometry` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.sacred_geometry import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.sacred_geometry import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.sacred_geometry not found in app utilities') from _e
