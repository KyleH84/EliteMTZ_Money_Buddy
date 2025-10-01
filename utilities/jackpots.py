from __future__ import annotations
# Bridge so `from utilities import jackpots` resolves
try:
    from AstroLotto.programs.utilities import jackpots  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities import jackpots  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.jackpots bridge could not find app copy') from _e
