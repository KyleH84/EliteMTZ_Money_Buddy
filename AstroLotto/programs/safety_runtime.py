from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Runtime clamping + predictions CSV self-heal
from typing import Dict, Any
from pathlib import Path
import csv, datetime as dt

try:
    from .smart_features import WHITE_RANGES, SPECIAL_RANGES
except Exception:
    from utilities.smart_features import WHITE_RANGES, SPECIAL_RANGES

DATA_DIR = Path(__file__).resolve().parents[2] / "Data"

def _clamp_white(game: str, nums):
    lo, hi, cnt = WHITE_RANGES.get(game, (1,70,5))
    out = []
    for n in nums or []:
        try:
            i = int(n)
            if i < lo: i = lo
            if i > hi: i = hi
            out.append(i)
        except Exception:
            continue
    return out[:cnt]

def _clamp_special(game: str, n):
    if game in SPECIAL_RANGES:
        lo, hi = SPECIAL_RANGES[game]
        try:
            i = int(n)
        except Exception:
            return ""
        if i < lo: i = lo
        if i > hi: i = hi
        return i
    return ""

def clamp_pick(game: str, pick: Dict[str,Any]) -> Dict[str,Any]:
    p = dict(pick or {})
    p["white"] = _clamp_white(game, p.get("white", []))
    if "special" in p and p.get("special") != "":
        p["special"] = _clamp_special(game, p.get("special"))
    return p

def _pred_path(game: str) -> Path:
    return DATA_DIR / f"{game}_predictions.csv"

def ensure_predictions_schema(game: str) -> None:
    path = _pred_path(game)
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["white_balls","draw_date","notes"]
    if game in ("powerball","megamillions","luckyforlife","colorado"):
        cols.insert(1, "special")
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(cols)
        return
    # Try to add missing columns
    try:
        import pandas as pd
        df = pd.read_csv(path, dtype=str).fillna("")
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        df = df[cols]
        df.to_csv(path, index=False)
    except Exception:
        pass

def append_prediction(game: str, pick: Dict[str,Any], note: str = "default") -> None:
    ensure_predictions_schema(game)
    p = clamp_pick(game, pick)
    row = {
        "white_balls": "[" + ",".join(str(int(x)) for x in p.get("white", [])) + "]",
        "draw_date": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "notes": note
    }
    if game in ("powerball","megamillions","luckyforlife","colorado"):
        row["special"] = ("" if p.get("special","")=="" else int(p.get("special")))
    path = _pred_path(game)
    header = list(row.keys()) if "special" in row else ["white_balls","draw_date","notes"]
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if path.stat().st_size == 0:
            w.writeheader()
        w.writerow(row)

def install():
    # No-op placeholder for import side-effects pattern
    return True
