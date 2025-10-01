from __future__ import annotations
# Auto-bridge so `utilities.cosmic_format` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.cosmic_format import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.cosmic_format import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.cosmic_format not found in app utilities') from _e
