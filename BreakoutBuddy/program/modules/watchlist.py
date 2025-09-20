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
from typing import Iterable, List
import duckdb

def ensure_watchlist(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            ticker VARCHAR,
            added_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            note VARCHAR
        )
    """)

def _norm_tickers(tickers: Iterable[str] | None) -> List[str]:
    out: List[str] = []
    for t in (tickers or []):
        if not t:
            continue
        t2 = str(t).strip().upper()
        if t2 and t2 not in out:
            out.append(t2)
    return out

def add_to_watchlist(conn, tickers: Iterable[str] | None) -> int:
    ensure_watchlist(conn)
    syms = _norm_tickers(tickers)
    if not syms:
        return 0
    n = 0
    for t in syms:
        try:
            conn.execute("INSERT INTO watchlist (ticker) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM watchlist WHERE ticker = ?)", [t, t])
            n += 1
        except Exception:
            pass
    return n

def remove_from_watchlist(conn, tickers: Iterable[str] | None) -> int:
    ensure_watchlist(conn)
    syms = _norm_tickers(tickers)
    if not syms:
        return 0
    q = "DELETE FROM watchlist WHERE ticker IN (" + ",".join(["?"] * len(syms)) + ")"
    conn.execute(q, syms)
    return len(syms)

def list_watchlist(conn) -> list[str]:
    ensure_watchlist(conn)
    try:
        df = conn.execute("SELECT ticker FROM watchlist ORDER BY ticker").fetchdf()
        return [str(x).upper() for x in df["ticker"].tolist()]
    except Exception:
        return []
