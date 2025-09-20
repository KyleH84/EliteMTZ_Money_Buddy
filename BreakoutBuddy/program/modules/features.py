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
from typing import Iterable, Optional, Sequence
import pandas as pd
import duckdb

# Columns we persist; extra columns are ignored safely.
FEATURE_COLS: Sequence[str] = [
    "Ticker","Close","ChangePct","RelSPY","RVOL","RSI4","ConnorRSI",
    "ATR","ADX","SqueezeOn","SqueezeHint","GapPct"
]

def _ensure_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS features_history (
            as_of TIMESTAMP,
            Ticker VARCHAR,
            Close DOUBLE,
            ChangePct DOUBLE,
            RelSPY DOUBLE,
            RVOL DOUBLE,
            RSI4 DOUBLE,
            ConnorRSI DOUBLE,
            ATR DOUBLE,
            ADX DOUBLE,
            SqueezeOn INTEGER,
            SqueezeHint DOUBLE,
            GapPct DOUBLE
        );
    """)
    con.execute("""
        
        CREATE OR REPLACE VIEW features_latest AS
        SELECT * EXCLUDE (rn) FROM (
            SELECT
                as_of, Ticker, Close, ChangePct, RelSPY, RVOL, RSI4,
                ConnorRSI, ATR, ADX, SqueezeOn, SqueezeHint, GapPct,
                ROW_NUMBER() OVER (PARTITION BY Ticker ORDER BY as_of DESC) AS rn
            FROM features_history
        ) WHERE rn = 1;
             
    """)

def persist_features(df: pd.DataFrame, db_path: Path | str, *, asof: Optional[pd.Timestamp] = None) -> int:
    """Append snapshot features into DuckDB and refresh features_latest view.
    Returns the number of rows written.
    """
    if df is None or df.empty or "Ticker" not in df.columns:
        return 0
    keep = [c for c in FEATURE_COLS if c in df.columns] + ["Ticker"]
    keep = list(dict.fromkeys(keep))  # dedupe while preserving order
    tmp = df[keep].copy()
    if tmp.empty:
        return 0
    asof = pd.Timestamp.utcnow().floor("min") if asof is None else pd.Timestamp(asof)
    tmp.insert(0, "as_of", asof)
    con = duckdb.connect(str(db_path))
    _ensure_table(con)
    con.register("tmp_df", tmp)
    con.execute("INSERT INTO features_history SELECT * FROM tmp_df")
    con.unregister("tmp_df")
    con.close()
    return len(tmp)

def load_features(db_path: Path | str, *, tickers: Optional[Iterable[str]] = None, latest: bool = True) -> pd.DataFrame:
    con = duckdb.connect(str(db_path))
    _ensure_table(con)
    if latest:
        if tickers:
            q = "SELECT * FROM features_latest WHERE upper(Ticker) IN (%s)" % ",".join(['?']*len(list(tickers)))
            df = con.execute(q, [t.upper() for t in tickers]).df()
        else:
            df = con.execute("SELECT * FROM features_latest").df()
    else:
        if tickers:
            q = "SELECT * FROM features_history WHERE upper(Ticker) IN (%s) ORDER BY asof DESC" % ",".join(['?']*len(list(tickers)))
            df = con.execute(q, [t.upper() for t in tickers]).df()
        else:
            df = con.execute("SELECT * FROM features_history ORDER BY asof DESC").df()
    con.close()
    return df
