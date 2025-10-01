from __future__ import annotations
# Auto-bridge so `utilities.predict_ui_common` resolves in Cloud/Local
try:
    from AstroLotto.programs.utilities.predict_ui_common import *  # type: ignore
except Exception:
    try:
        from BreakoutBuddy.program.utilities.predict_ui_common import *  # type: ignore
    except Exception as _e:
        raise ModuleNotFoundError('utilities.predict_ui_common not found in app utilities') from _e
