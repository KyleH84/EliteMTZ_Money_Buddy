from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from pathlib import Path

# ---------- Strict per-app Data/Extras resolver (BreakoutBuddy) ----------
from pathlib import Path
import os, sys
BB_HERE     = Path(__file__).resolve()
BB_APP_ROOT = BB_HERE.parents[1]   # .../BreakoutBuddy

def _bb_cloud_roots():
    h = Path.home()
    return [
        h / "OneDrive",
        h / "OneDrive - Personal",
        h / "OneDrive - Wagstaff Law Firm",
        h / "Dropbox",
        h / "Google Drive",
        h / "Library" / "CloudStorage" / "OneDrive",
        h / "Library" / "CloudStorage" / "Dropbox",
        h / "Library" / "CloudStorage" / "GoogleDrive",
    ]

def _bb_first_existing(paths):
    for p in paths:
        try:
            p2 = Path(p).expanduser().resolve()
            if p2.exists():
                return p2
        except Exception:
            pass
    return None

def bb_resolve_dir(preferred_env_var: str, fallback_name: str):
    """
    Strict per-app order (NO repo-level fallback):
      1) Env var (abs or relative)
      2) BB_APP_ROOT/<name>
      3) CWD/<name>
      4) Cloud roots: <BreakoutBuddy>/<name>
      5) Create BB_APP_ROOT/<name>
    """
    envv = os.environ.get(preferred_env_var, "").strip()
    if envv:
        cand = (Path(envv) if os.path.isabs(envv) else (Path.cwd() / envv))
        if cand.exists():
            return cand.resolve()

    hit = _bb_first_existing([BB_APP_ROOT / fallback_name, Path.cwd() / fallback_name])
    if hit:
        return hit

    cands = []
    for root in _bb_cloud_roots():
        cands += [
            root / BB_APP_ROOT.name / fallback_name,
            root / "Projects" / BB_APP_ROOT.name / fallback_name,
        ]
    hit = _bb_first_existing(cands)
    if hit:
        return hit

    target = (BB_APP_ROOT / fallback_name).resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target

BB_DATA   = bb_resolve_dir("BREAKOUTBUDDY_DATA",   "Data")
BB_EXTRAS = bb_resolve_dir("BREAKOUTBUDDY_EXTRAS", "extras")

bb_extras_src = (BB_EXTRAS / "src")
if bb_extras_src.exists() and str(bb_extras_src) not in sys.path:
    sys.path.insert(0, str(bb_extras_src))
# ---------- end resolver ----------
from typing import Dict, Any, List, Optional
import duckdb
import pandas as pd

DB_PATH = (Path(__file__).resolve().parents[3] / "Data" / str(BB_DATA / 'breakoutbuddy.duckdb'))

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
