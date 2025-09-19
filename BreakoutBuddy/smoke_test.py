
from pathlib import Path
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
for p in [ROOT/"Data/buddy.duckdb"]:
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
