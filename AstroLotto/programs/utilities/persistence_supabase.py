from __future__ import annotations
try:
    from BreakoutBuddy.program.modules.services.persistence_supabase import save_table as _save, load_table as _load
    def save_table(table_name: str, df, app: str = "AL") -> None: _save(table_name, df, app=app)
    def load_table(table_name: str, app: str = "AL"):
        return _load(table_name, app=app)
except Exception:
    def save_table(table_name: str, df, app: str = "AL") -> None:  # no-op
        return None
    def load_table(table_name: str, app: str = "AL"):
        import pandas as pd
        return pd.DataFrame()
