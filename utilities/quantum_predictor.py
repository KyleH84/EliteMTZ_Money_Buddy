from __future__ import annotations
# Auto-bridge so `utilities.quantum_predictor` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.quantum_predictor import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.quantum_predictor import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.quantum_predictor not found in app utilities') from _e
