# Program/historical_backfill.py (v10.9 same API as 10.8)
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
try:
    import requests
except Exception:
    requests = None

DATA = Path(os.environ.get("ASTRO_DATA_DIR", Path.cwd() / "Data"))
DATA.mkdir(parents=True, exist_ok=True)

def _norm_game(game: str) -> str:
    g = (game or "").lower().strip()
    if g.startswith("mega"): return "megamillions"
    if g.startswith("power"): return "powerball"
    if "colorado" in g and "lotto" in g: return "colorado_lottery"
    if g.replace(" ", "") in ("cash5","cashfive"): return "cash5"
    if g.replace(" ", "") in ("lfl","luckyforlife"): return "lucky_for_life"
    return g

def _read_csv(path: Path) -> pd.DataFrame:
    try: return pd.read_csv(path)
    except Exception: return pd.DataFrame()

def _write_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True); df.to_csv(path, index=False)

def _merge_append(existing: pd.DataFrame, new: pd.DataFrame, date_col="draw_date") -> pd.DataFrame:
    if existing is None or existing.empty: out = new.copy()
    else:
        out = pd.concat([existing, new], ignore_index=True)
        out = out.drop_duplicates(subset=[date_col], keep="last") if date_col in out.columns else out.drop_duplicates(keep="last")
    if date_col in out.columns:
        out[date_col] = pd.to_datetime(out[date_col], errors="coerce").dt.date
        out = out.sort_values(date_col)
    return out

def _ny_endpoint(game: str) -> Optional[str]:
    if game == "megamillions": return "https://data.ny.gov/resource/5xaw-6ayf.json?$limit=50000"
    if game == "powerball": return "https://data.ny.gov/resource/d6yy-54nr.json?$limit=50000"
    return None

def _fetch_ny(game: str) -> Optional[pd.DataFrame]:
    if requests is None: return None
    url = _ny_endpoint(game)
    if not url: return None
    try:
        r = requests.get(url, timeout=20); r.raise_for_status()
        js = r.json(); rows=[]
        for it in js:
            try:
                dd = it.get("draw_date") or it.get("draw_date_")
                if not dd: continue
                d = pd.to_datetime(dd).date()
                nums = (it.get("winning_numbers") or "").replace(","," ").split()
                nums = [int(x) for x in nums if str(x).isdigit()]
                special = int(it.get("mega_ball") or it.get("megaball") or it.get("powerball") or it.get("pb") or 0)
                row = {"draw_date": d}
                for i,n in enumerate(nums[:6], start=1): row[f"white{i}"] = n
                row["special"] = special; rows.append(row)
            except Exception: continue
        if not rows: return None
        return pd.DataFrame(rows)
    except Exception: return None

def _fetch_powerball_official() -> Optional[pd.DataFrame]:
    if requests is None: return None
    url = "https://www.powerball.com/api/v1/numbers/powerball/recent?_format=json"
    try:
        r = requests.get(url, timeout=20); r.raise_for_status()
        js = r.json(); rows=[]
        for it in js:
            try:
                d = pd.to_datetime(it.get("field_draw_date")).date()
                balls = str(it.get("field_winning_numbers") or "").split()
                balls = [int(x) for x in balls if str(x).isdigit()]
                pb = int(it.get("field_powerball") or 0)
                row = {"draw_date": d}
                for i,n in enumerate(balls[:6], start=1): row[f"white{i}"] = n
                row["special"] = pb; rows.append(row)
            except Exception: continue
        return pd.DataFrame(rows) if rows else None
    except Exception: return None

def fetch_history(game: str) -> Optional[pd.DataFrame]:
    g = _norm_game(game)
    if g == "powerball": return _fetch_ny("powerball") or _fetch_powerball_official()
    if g == "megamillions": return _fetch_ny("megamillions")
    return None

def ensure_history_csv(path: str, game: Optional[str] = None) -> Dict[str, Any]:
    p = Path(path)
    if not game:
        name = p.stem.lower()
        if "mega" in name: game="megamillions"
        elif "power" in name: game="powerball"
        else: game=""
    g = _norm_game(game)
    if g not in ("powerball","megamillions"):
        return {"ok": True, "game": g, "path": str(p), "added_rows": 0, "note": "game not supported for HTTP backfill"}
    existing = _read_csv(p)
    before = 0 if existing.empty else len(existing)
    df = fetch_history(g)
    if df is None or df.empty:
        if existing.empty and not p.exists():
            cols = ["draw_date","white1","white2","white3","white4","white5","special"]; _write_csv(pd.DataFrame(columns=cols), p)
        return {"ok": False, "game": g, "path": str(p), "added_rows": 0, "note": "no data fetched"}
    if g=="powerball": wmax,smax=69,26
    else: wmax,smax=70,25
    for i in range(1,7):
        c=f"white{i}"
        if c in df.columns:
            df[c]=pd.to_numeric(df[c], errors="coerce").astype("Int64")
            df.loc[(df[c]<1)|(df[c]>wmax), c]=pd.NA
    if "special" in df.columns:
        df["special"]=pd.to_numeric(df["special"], errors="coerce").astype("Int64")
        df.loc[(df["special"]<1)|(df["special"]>smax),"special"]=pd.NA
    out=_merge_append(existing, df, "draw_date")
    after=0 if out.empty else len(out)
    _write_csv(out, p)
    return {"ok": True, "game": g, "path": str(p), "added_rows": max(0, after-before)}

# Legacy API
def backfill(game: Optional[str]=None, path: Optional[str]=None, **kwargs): 
    if path is None and game: path= str(Path(DATA) / f"cached_{_norm_game(game)}_data.csv")
    if path is None: return {"ok": False, "message": "backfill requires a game or a path"}
    return ensure_history_csv(str(path), game=game or "")
def backfill_for_csv(path: str, game: Optional[str]=None, **kwargs): return ensure_history_csv(path, game=game or "")
def run_backfill_for_csv(path: str, game: Optional[str]=None, **kwargs): return ensure_history_csv(path, game=game or "")
def backfill_game_to_csv(game: str, path: str, **kwargs): return ensure_history_csv(path, game=game or "")
def fill_missing_draws(path: str, game: Optional[str]=None, **kwargs): return ensure_history_csv(path, game=game or "")
