from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
import time

# Cloud-safe Data dir resolver
try:
    from .cloud_paths import resolve_data_dir  # type: ignore
except Exception:
    def resolve_data_dir(app_root: Path, env_var_name: str, default_subdir: str) -> Path:
        p = app_root / default_subdir
        p.mkdir(parents=True, exist_ok=True)
        return p

# Optional Supabase helpers (best-effort)
try:
    from .persistence_supabase import save_table as _save_table, load_table as _load_table  # type: ignore
except Exception:
    _save_table = None
    _load_table = None

APP_ROOT = Path(__file__).resolve().parents[2]  # .../AstroLotto/programs
DATA_DIR = resolve_data_dir(APP_ROOT, "ASTROLOTTO_DATA", "Data")
CACHE = DATA_DIR / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
JACKPOT_FILE = CACHE / "jackpots.json"

# ---- Supabase helpers ----
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
        val = int(sub.iloc[0]["Value"])
        # stale guard: older than 10 days? ignore
        try:
            asof = sub.iloc[0]["AsOf"]
            # If it’s a string, try parse
            import pandas as pd
            ts = pd.to_datetime(asof, utc=True, errors="coerce")
            if pd.notna(ts):
                age_days = (pd.Timestamp.utcnow(tz="UTC") - ts).days
                if age_days > 10:
                    return None
        except Exception:
            pass
        return val
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

# ---- Official API fetchers (best-effort) ----
def _fetch_powerball_api() -> Optional[int]:
    try:
        import requests
        url = "https://www.powerball.com/api/v1/estimates/powerball?_format=json"
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        data = r.json()
        # API returns a list of dicts; take the first estimate's 'jackpot' or 'amount'
        if isinstance(data, list) and data:
            first = data[0]
            for k in ("jackpot", "amount", "estimated_jackpot", "value"):
                if k in first and str(first[k]).strip():
                    return int(str(first[k]).replace(",", ""))
    except Exception:
        pass
    return None

def _fetch_megamillions_api() -> Optional[int]:
    try:
        import requests
        # Known JSON endpoint; if changed, this gracefully fails
        url = "https://www.megamillions.com/api/Jackpot/CurrentJackpot"
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        data = r.json()
        # Common fields: 'Jackpot', 'NextJackpot', 'JackpotAmount'
        for k in ("Jackpot", "NextJackpot", "JackpotAmount", "Amount"):
            if k in data and str(data[k]).strip():
                return int(str(data[k]).replace(",", ""))
    except Exception:
        pass
    return None

# ---- Local cache helpers ----
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

# ---- Public API ----
def get_jackpot(name: str) -> int:
    key = name.strip()
    # 1) Local overrides/cache first
    d = _read_cache()
    if key in d:
        try:
            return int(d[key])
        except Exception:
            pass

    # 2) Supabase latest (fast, no scraping)
    val = _from_supabase(key)
    if isinstance(val, int) and val > 0:
        return val

    # 3) Official APIs — best-effort by name
    fetched: Optional[int] = None
    lname = key.lower()
    if "power" in lname:
        fetched = _fetch_powerball_api()
    elif "mega" in lname:
        fetched = _fetch_megamillions_api()

    if isinstance(fetched, int) and fetched > 0:
        # persist
        d[key] = int(fetched)
        _write_cache(d)
        _save_supabase(key, int(fetched))
        return int(fetched)

    # 4) Last-resort: return 0 so UI shows n/a
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
