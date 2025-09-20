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
