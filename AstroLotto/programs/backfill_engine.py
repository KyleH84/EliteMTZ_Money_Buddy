
# Program/backfill_engine.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional
import pandas as pd

from utilities import draws as _draws
from history_normalizer import _harmonize_to_cached_schema

APP_DIR = Path(__file__).resolve().parent        # Program/
PROJECT_DIR = APP_DIR.parent                     # project root
# Prefer project_root/Data, else Program/Data, else create project_root/Data
DATA_CANDIDATES = [PROJECT_DIR / "Data", APP_DIR / "Data"]
for _d in DATA_CANDIDATES:
    if _d.exists():
        DATA = _d
        break
else:
    DATA = PROJECT_DIR / "Data"
    DATA.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "powerball": DATA / "cached_powerball_data.csv",
    "megamillions": DATA / "cached_megamillions_data.csv",
    "colorado": DATA / "cached_colorado_lottery_data.csv",
    "cash5": DATA / "cached_cash5_data.csv",
    "pick3": DATA / "cached_pick3_data.csv",
    "luckyforlife": DATA / "cached_luckyforlife_data.csv",
}

DRAW_KEYS = {
    "powerball": "powerball",
    "megamillions": "mega_millions",
    "colorado": "colorado_lottery",
    "cash5": "cash5",
    "pick3": "pick3",
    "luckyforlife": "lucky_for_life",
}

def _read_csv(path: Path) -> pd.DataFrame:
    try: return pd.read_csv(path)
    except Exception: return pd.DataFrame()

def _merge_dedupe(existing: pd.DataFrame, new: pd.DataFrame, date_col="draw_date") -> pd.DataFrame:
    if existing is None or existing.empty: out = new.copy()
    else:
        out = pd.concat([existing, new], ignore_index=True)
        out = out.drop_duplicates(subset=[date_col], keep="last") if date_col in out.columns else out.drop_duplicates(keep="last")
    if date_col in out.columns:
        out[date_col] = pd.to_datetime(out[date_col], errors="coerce").dt.date.astype(str)
        out = out.dropna(subset=[date_col]).sort_values(date_col)
    return out

def _to_cached_schema_from_draws_csv(raw_csv: Path, target: Path) -> pd.DataFrame:
    import pandas as pd
    if not raw_csv.exists(): return pd.DataFrame(columns=["draw_date"])
    df = _read_csv(raw_csv)
    if df.empty: return pd.DataFrame(columns=["draw_date"])
    work = df.copy()
    work.columns = [str(c).strip().lower() for c in work.columns]
    if "date" in work.columns:
        work["draw_date"] = pd.to_datetime(work["date"], errors="coerce").dt.date.astype(str)
    elif "draw_date" in work.columns:
        work["draw_date"] = pd.to_datetime(work["draw_date"], errors="coerce").dt.date.astype(str)
    else:
        work["draw_date"] = ""

    name = target.name
    out = pd.DataFrame({"draw_date": work["draw_date"]})

    if "powerball" in name or "megamillions" in name or "luckyforlife" in name:
        for i in range(1, 6): out[f"white{i}"] = pd.to_numeric(work.get(f"n{i}"), errors="coerce").astype("Int64")
        out["special"] = pd.to_numeric(work.get("s1"), errors="coerce").astype("Int64")
    elif "colorado" in name:
        for i in range(1, 7): out[f"n{i}"] = pd.to_numeric(work.get(f"n{i}"), errors="coerce").astype("Int64")
    elif "cash5" in name:
        for i in range(1, 6): out[f"n{i}"] = pd.to_numeric(work.get(f"n{i}"), errors="coerce").astype("Int64")
    elif "pick3" in name:
        for i in range(1, 4):
            out[f"n{i}"] = pd.to_numeric(work.get(f"n{i}"), errors="coerce").astype("Int64")
            out[f"d{i}"] = out[f"n{i}"]

    try:
        out = _harmonize_to_cached_schema(out, target)
    except Exception:
        pass

    if "draw_date" in out.columns:
        out["draw_date"] = pd.to_datetime(out["draw_date"], errors="coerce").dt.date.astype(str)
        out = out.dropna(subset=["draw_date"]).sort_values("draw_date")
    return out

def _update_one(game: str, years_back: int = 15) -> int:
    if game not in TARGETS: return 0
    target = TARGETS[game]
    draw_key = DRAW_KEYS[game]
    scratch = DATA / f"raw_{game}.csv"
    try:
        _draws.update_draws_since_last(draw_key, str(scratch), years_back=years_back)
    except Exception:
        pass
    df_new = _to_cached_schema_from_draws_csv(scratch, target)
    if df_new is None or df_new.empty:
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(columns=["draw_date"]).to_csv(target, index=False)
        return 0
    existing = _read_csv(target)
    merged = _merge_dedupe(existing, df_new, date_col="draw_date")
    target.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(target, index=False)
    return len(merged)

def backfill_all() -> Dict[str, int]:
    out: Dict[str, int] = {}
    for g in ("powerball","megamillions","colorado","cash5","pick3","luckyforlife"):
        try:
            out[g] = _update_one(g, years_back=15)
        except Exception:
            out[g] = 0
    return out

def backfill(game: Optional[str] = None) -> Dict[str, int]:
    if not game: return backfill_all()
    g = (game or "").strip().lower()
    return {g: _update_one(g, years_back=15)}

def run() -> Dict[str, int]:
    return backfill_all()
