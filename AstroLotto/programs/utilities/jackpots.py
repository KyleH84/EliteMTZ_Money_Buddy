from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

try:
    from .cloud_paths import resolve_data_dir  # type: ignore
except Exception:
    def resolve_data_dir(app_root: Path, env_var_name: str, default_subdir: str) -> Path:
        p = app_root / default_subdir
        p.mkdir(parents=True, exist_ok=True)
        return p

try:
    from .persistence_supabase import save_table as _save_table, load_table as _load_table  # type: ignore
except Exception:
    _save_table = None
    _load_table = None

APP_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = resolve_data_dir(APP_ROOT, "ASTROLOTTO_DATA", "Data")
CACHE = DATA_DIR / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
JACKPOT_FILE = CACHE / "jackpots.json"

def _read_cache() -> dict:
    try:
        if JACKPOT_FILE.exists():
            return json.loads(JACKPOT_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _write_cache(d: dict) -> None:
    try:
        JACKPOT_FILE.write_text(json.dumps(d), encoding="utf-8")
    except Exception:
        pass

def _from_supabase(name: str) -> Optional[int]:
    if _load_table is None:
        return None
    try:
        df = _load_table("jackpots_latest", app="AL")
        if df is None or df.empty:
            return None
        sub = df[df["Key"] == name].sort_values("AsOf", ascending=False)
        if sub.empty:
            return None
        val = int(str(sub.iloc[0]["Value"]).replace(",", ""))
        return val if val > 0 else None
    except Exception:
        return None

def _save_supabase(name: str, value: int) -> None:
    if _save_table is None:
        return
    try:
        import pandas as pd
        df = pd.DataFrame([{"Key": name, "Value": int(value), "AsOf": pd.Timestamp.utcnow()}])
        _save_table("jackpots_latest", df, app="AL")
    except Exception:
        pass

def _fetch_powerball_api() -> Optional[int]:
    try:
        import requests
        r = requests.get("https://www.powerball.com/api/v1/estimates/powerball?_format=json", timeout=6)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            first = data[0]
            for k in ("jackpot","amount","estimated_jackpot","value"):
                if k in first and str(first[k]).strip():
                    val = int(str(first[k]).replace(",", ""))
                    return val if val > 0 else None
    except Exception:
        pass
    return None

def _fetch_megamillions_api() -> Optional[int]:
    try:
        import requests
        r = requests.get("https://www.megamillions.com/api/Jackpot/CurrentJackpot", timeout=6)
        r.raise_for_status()
        data = r.json()
        for k in ("Jackpot","NextJackpot","JackpotAmount","Amount","value"):
            if k in data and str(data[k]).strip():
                val = int(str(data[k]).replace(",", ""))
                return val if val > 0 else None
    except Exception:
        pass
    return None

def get_jackpot(name: str) -> int:
    key = name.strip()
    # 1) cache first, but ignore non-positive values
    d = _read_cache()
    if key in d:
        try:
            cached = int(str(d[key]).replace(",", ""))
            if cached > 0:
                return cached
        except Exception:
            pass

    # 2) Supabase
    sb = _from_supabase(key)
    if isinstance(sb, int) and sb > 0:
        d[key] = int(sb)
        _write_cache(d)
        return int(sb)

    # 3) APIs by name (permissive matching)
    lname = key.lower().replace(" ", "")
    val = None
    if "power" in lname:
        val = _fetch_powerball_api()
    elif "mega" in lname:
        val = _fetch_megamillions_api()

    if isinstance(val, int) and val > 0:
        d[key] = int(val)
        _write_cache(d)
        _save_supabase(key, int(val))
        return int(val)

    return 0

def set_override(name: str, value: int) -> None:
    d = _read_cache()
    d[name.strip()] = int(value)
    _write_cache(d)
    _save_supabase(name.strip(), int(value))

def clear_override(name: str) -> None:
    d = _read_cache()
    if name.strip() in d:
        d.pop(name.strip(), None)
        _write_cache(d)
