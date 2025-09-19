
from __future__ import annotations
from typing import Tuple, Optional
import duckdb
from .cache import _conn

def get_locked_cap() -> Tuple[bool, Optional[float]]:
    """Return (enabled, cap_high) if a lock is set, else (False, None)."""
    con = _conn()
    try:
        con.execute("""
        CREATE TABLE IF NOT EXISTS AgentCapLock(
            Date TIMESTAMP,
            Enabled BOOLEAN,
            CapHigh DOUBLE
        )""")
        df = con.execute("""
            SELECT Enabled, CapHigh 
            FROM AgentCapLock
            ORDER BY Date DESC
            LIMIT 1
        """).fetchdf()
        if df is None or df.empty:
            return False, None
        en = bool(df.iloc[0]['Enabled'])
        val = float(df.iloc[0]['CapHigh']) if df.iloc[0]['CapHigh'] is not None else None
        return en, val
    except Exception:
        return False, None

def set_locked_cap(enabled: bool, cap_high: float) -> None:
    con = _conn()
    con.execute("""
        CREATE TABLE IF NOT EXISTS AgentCapLock(
            Date TIMESTAMP,
            Enabled BOOLEAN,
            CapHigh DOUBLE
        )""")
    con.execute("""INSERT INTO AgentCapLock SELECT current_timestamp, ?, ?""", [bool(enabled), float(cap_high)])
