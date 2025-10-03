# This file is a patched version that optionally saves latest jackpots to Supabase.
from __future__ import annotations
from pathlib import Path
import json
import time

from .cloud_paths import resolve_data_dir

APP_ROOT = Path(__file__).resolve().parents[2]  # .../AstroLotto/programs
DATA_DIR = resolve_data_dir(APP_ROOT, "ASTROLOTTO_DATA", "Data")
CACHE = DATA_DIR / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

JACKPOT_FILE = CACHE / "jackpots.json"

def _fetch_latest() -> dict:
    # Placeholder: your existing jackpot fetching logic should live here.
    # For safety, keep structure; if you already have real logic, this call will be bypassed by your original code.
    return {"Powerball": 0, "MegaMillions": 0}

def get_jackpot(name: str) -> int:
    try:
        if JACKPOT_FILE.exists():
            d = json.loads(JACKPOT_FILE.read_text(encoding="utf-8"))
            if name in d:
                return int(d[name])
    except Exception:
        pass
    # Fallback:
    latest = _fetch_latest()
    val = int(latest.get(name, 0))
    try:
        _save_latest_to_supabase(name, val)
    except Exception:
        pass
    return val

def set_override(name: str, value: int) -> None:
    try:
        d = json.loads(JACKPOT_FILE.read_text(encoding="utf-8")) if JACKPOT_FILE.exists() else {}
    except Exception:
        d = {}
    d[name] = int(value)
    JACKPOT_FILE.write_text(json.dumps(d), encoding="utf-8")
    try:
        _save_latest_to_supabase(name, int(value))
    except Exception:
        pass

def clear_override(name: str) -> None:
    try:
        d = json.loads(JACKPOT_FILE.read_text(encoding="utf-8")) if JACKPOT_FILE.exists() else {}
        if name in d:
            d.pop(name, None)
            JACKPOT_FILE.write_text(json.dumps(d), encoding="utf-8")
    except Exception:
        pass

def _save_latest_to_supabase(key: str, val: int) -> None:
    try:
        import pandas as pd
        from .persistence_supabase import save_table
        df = pd.DataFrame([{'Key': key, 'Value': int(val), 'AsOf': pd.Timestamp.utcnow()}])
        save_table('jackpots_latest', df, app='AL')
    except Exception:
        # non-fatal
        pass
