
from __future__ import annotations
import duckdb
from .agents.cache import ensure_indexes, _conn

def ensure_db_ready():
    con = _conn()
    ensure_indexes()
    return True

def health_snapshot():
    con = _conn()
    stats = {}
    try:
        stats['AgentCache_24h'] = int(con.execute("SELECT count(*) FROM AgentCache WHERE AsOf > current_timestamp - INTERVAL '1' DAY").fetchone()[0])
    except Exception:
        stats['AgentCache_24h'] = 0
    try:
        stats['AgentCalib_rows'] = int(con.execute("SELECT count(*) FROM AgentCalib").fetchone()[0])
    except Exception:
        stats['AgentCalib_rows'] = 0
    try:
        stats['AgentWeights_versions'] = int(con.execute("SELECT count(*) FROM AgentWeights").fetchone()[0])
    except Exception:
        stats['AgentWeights_versions'] = 0
    return stats
