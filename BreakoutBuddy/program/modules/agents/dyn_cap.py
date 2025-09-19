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

from __future__ import annotations
from typing import Optional
import duckdb
import pandas as pd

from .cache import _conn

def _latest_agentcalib(con=None) -> pd.DataFrame:
    con = con or _conn()
    try:
        df = con.execute("""
            SELECT Date, BinLow, BinHigh, Count, HitRate
            FROM AgentCalib
            WHERE Metric='AgentsScore'
            QUALIFY row_number() OVER (ORDER BY Date DESC) = 1
        """).fetchdf()
        return df
    except Exception:
        return pd.DataFrame()

def get_agents_multiplier_cap(default_cap: float = 1.15) -> float:
    """Compute an adaptive cap for the Agents multiplier.
    Returns a value in [1.10, 1.18] where higher = more trust in agents.
    Based on sample size (Count) and calibration MAE vs diagonal.
    """
    df = _latest_agentcalib()
    if df is None or df.empty:
        return float(default_cap)
    df = df.copy()
    try:
        df['Mid'] = (df['BinLow'].astype(float) + df['BinHigh'].astype(float)) / 2.0
        df['AbsErr'] = (df['HitRate'].astype(float) - df['Mid']).abs()
        n = float(df['Count'].astype(float).sum())
        if n <= 0:
            return float(default_cap)
        mae = float((df['AbsErr'] * df['Count']).sum() / n)
        # Confidence from size & error: more rows, lower error → higher confidence
        size_term = min(1.0, n / 1000.0)              # saturates at 1000 samples
        error_term = max(0.0, 1.0 - min(1.0, mae / 0.08))  # 0 error →1, 8% abs error →0
        conf_score = size_term * error_term           # 0..1
        cap = 1.10 + 0.08 * conf_score
        return float(max(1.10, min(1.18, cap)))
    except Exception:
        return float(default_cap)
