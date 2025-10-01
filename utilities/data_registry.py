from __future__ import annotations
# Root shim: forward to BreakoutBuddy.program.utilities.data_registry
try:
    from BreakoutBuddy.program.utilities.data_registry import *  # type: ignore
except Exception as _e:
    import time as _t
    def load_active_snapshot(epoch: int):
        import pandas as _pd
        return _pd.DataFrame(), "shim://no-snapshot"
    def get_refresh_epoch() -> int:
        return int(_t.time())