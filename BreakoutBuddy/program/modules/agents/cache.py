from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Optional
import duckdb
import pandas as pd

DB_PATH = (Path(__file__).resolve().parents[3] / "Data" / "breakoutbuddy.duckdb")

def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute("""
    CREATE TABLE IF NOT EXISTS AgentCache(
        Ticker TEXT,
        AsOf TIMESTAMP,
        PriorPUp DOUBLE,
        HistHash TEXT,
        Sentiment JSON,
        Technical JSON,
        AgentsScore DOUBLE,
        AgentsConf DOUBLE,
        AgentsLabel TEXT,
        AgentsWhy TEXT,
        Headlines JSON,
        ExpiresAt TIMESTAMP
    );
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS AgentCalib(
        Date DATE,
        BinLow DOUBLE,
        BinHigh DOUBLE,
        Count BIGINT,
        HitRate DOUBLE,
        Metric TEXT
    );
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS AgentWeights(
        Date TIMESTAMP,
        w0 DOUBLE,
        w_model DOUBLE,
        w_tech DOUBLE,
        w_sent DOUBLE
    );
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS AgentCapLock(
        Date TIMESTAMP,
        Enabled BOOLEAN,
        CapHigh DOUBLE
    );
    """)
    return con

def ensure_indexes():
    con = _conn()
    try:
        con.execute("CREATE INDEX IF NOT EXISTS idx_agentcache_ta ON AgentCache(Ticker, AsOf)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_agentcalib_date ON AgentCalib(Date)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_agentweights_date ON AgentWeights(Date)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_agentcaplock_date ON AgentCapLock(Date)")
    except Exception:
        pass

def put_cache(df: pd.DataFrame, expires_minutes: int = 60) -> int:
    if df is None or df.empty:
        return 0
    con = _conn()
    dfc = df.copy()
    con.register("tmp_agents", dfc)
    con.execute("INSERT INTO AgentCache SELECT * FROM tmp_agents")
    con.unregister("tmp_agents")
    return len(dfc)

def latest_weights() -> Optional[Dict[str, float]]:
    con = _conn()
    try:
        row = con.execute("SELECT w0, w_model, w_tech, w_sent FROM AgentWeights ORDER BY Date DESC LIMIT 1").fetchone()
        if row:
            w0, w_model, w_tech, w_sent = row
            return {"w0": float(w0), "w_model": float(w_model), "w_tech": float(w_tech), "w_sent": float(w_sent)}
    except Exception:
        return None
    return None
