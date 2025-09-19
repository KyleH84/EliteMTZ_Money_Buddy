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
from typing import List
import numpy as np
import pandas as pd
import duckdb
from datetime import datetime, timedelta
from .cache import _conn

from ..labels import compute_labels_for_symbol

def _bin_stats(scores: pd.Series, hits: pd.Series, bins: List[float]) -> pd.DataFrame:
    b = pd.cut(scores, bins=bins, include_lowest=True, right=True)
    g = hits.groupby(b)
    out = pd.DataFrame({
        "Count": g.size(),
        "HitRate": g.mean(),
    }).reset_index().rename(columns={"score":"Bin"})
    out["BinLow"] = out["Bin"].apply(lambda x: float(x.left) if hasattr(x, "left") else np.nan)
    out["BinHigh"] = out["Bin"].apply(lambda x: float(x.right) if hasattr(x, "right") else np.nan)
    return out[["BinLow","BinHigh","Count","HitRate"]]

def run_agents_calibration(lookback_days: int = 120, horizon_days: int = 5, target_pct: float = 3.0) -> pd.DataFrame:
    """Compute reliability bins for AgentsScore versus +target_pct% in horizon_days."""
    con = _conn()
    since = f"current_timestamp - INTERVAL '{int(lookback_days)}' DAY"
    df = con.execute(f"""
        SELECT Ticker, AsOf::DATE as AsOfDate, AgentsScore, PriorPUp
        FROM AgentCache
        WHERE AsOf > {since}
        ORDER BY AsOf DESC
    """).fetchdf()

    if df.empty:
        return pd.DataFrame()

    # For each (Ticker, AsOfDate) compute forward label using yfinance via labels util
    rows = []
    for sym, g in df.groupby("Ticker"):
        lab = compute_labels_for_symbol(sym, horizon=horizon_days, target_pct=target_pct)
        if lab is None or lab.empty:
            continue
        lab["Date"] = pd.to_datetime(lab["Date"]).dt.tz_localize(None)
        lab.set_index("Date", inplace=True)
        for _, r in g.iterrows():
            asof = pd.to_datetime(r["AsOfDate"])
            try:
                # align to the closest trading day <= AsOf
                if asof not in lab.index:
                    # shift to previous available date
                    prev = lab.index[lab.index <= asof]
                    if len(prev)==0:
                        continue
                    asof_use = prev.max()
                else:
                    asof_use = asof
                col = f"Hit_+{int(target_pct)}in{horizon_days}d"
                hit = int(lab.loc[asof_use, col])
                rows.append({"Ticker": sym, "AsOfDate": asof_use, "AgentsScore": float(r["AgentsScore"]), "Hit": hit})
            except Exception:
                continue

    if not rows:
        return pd.DataFrame()

    df2 = pd.DataFrame(rows)
    bins = [0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0]
    stats = _bin_stats(df2["AgentsScore"], df2["Hit"], bins=bins)
    stats["Metric"] = "AgentsScore"

    # Write to DB
    con.register("tmp_stats", stats)
    con.execute("DELETE FROM AgentCalib WHERE Metric = 'AgentsScore'")
    con.execute("INSERT INTO AgentCalib SELECT current_date, BinLow, BinHigh, Count, HitRate, Metric FROM tmp_stats")
    return stats
