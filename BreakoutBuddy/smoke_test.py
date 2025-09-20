
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
import json, sys
import pandas as pd

ROOT = Path(__file__).resolve().parent
data_dir = ROOT/"Data"
ok = True

# Check configs
for p in [ROOT/"extras/engines_settings.json", ROOT/"extras/app_settings.json"]:
    try:
        obj = json.loads(p.read_text())
    except Exception as e:
        print(f"[FAIL] Config {p}: {e}"); ok=False
    else:
        print(f"[OK]   Config {p}: {list(obj)[:4]}")

# Check DuckDB
for p in [ROOT/str(BB_DATA / 'buddy.duckdb')]:
    if p.exists():
        print(f"[OK]   DB present: {p.name}")
    else:
        print(f"[WARN] DB missing (first run will create): {p.name}")

# Check snapshot pipeline (light)
try:
    from program.modules.services import scoring as scoring_svc
    class S: pass
    s = S(); s.universe_size=50; s.top_n=20
    snap, regime, ranked, _, _ = scoring_svc.rank_now(settings=s, top_n=20)
    need = ["Ticker","Close","RVOL","RSI4","EngineScore","EngineReasons"]
    for col in need:
        assert col in snap.columns, f"Missing {col} in snapshot"
    print(f"[OK]   Snapshot columns present: {', '.join(need)}")
    print(f"[OK]   Ranked rows: {len(ranked)}")
except Exception as e:
    print(f"[FAIL] Snapshot pipeline: {e}"); ok=False

sys.exit(0 if ok else 1)
