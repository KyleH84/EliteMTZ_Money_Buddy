from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


# programs/training_engine.py — trainer with canonical special_max clamp
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
MODELS = DATA / "models"
MODELS.mkdir(parents=True, exist_ok=True)

GAME_TO_CACHE = {
    "powerball": "cached_powerball_data.csv",
    "megamillions": "cached_megamillions_data.csv",
    "cash5": "cached_cash5_data.csv",
    "pick3": "cached_pick3_data.csv",
    "luckyforlife": "cached_luckyforlife_data.csv",
    "colorado": "cached_colorado_lottery_data.csv",
}

CANON_SPECIAL_MAX = {"powerball": 26, "megamillions": 25, "luckyforlife": 18}

def _read_cache(game: str) -> pd.DataFrame:
    path = DATA / GAME_TO_CACHE[game]
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def _series_int(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").dropna().astype(int)

def _detect_schema(df: pd.DataFrame):
    cols_l = [c.lower() for c in df.columns]
    lc_map = {c.lower(): c for c in df.columns}
    if "digits" in cols_l or all(c in cols_l for c in ["n1","n2","n3"]):
        whites = [lc_map.get("n1"), lc_map.get("n2"), lc_map.get("n3")]
        whites = [w for w in whites if w]
        return {"kind":"pick3", "white_cols": whites, "special": None, "white_count": 3}
    white_cols = [lc_map[c] for c in cols_l if c.startswith("white")]
    if not white_cols:
        for i in range(1, 8):
            key = f"n{i}"
            if key in cols_l:
                white_cols.append(lc_map[key])
    special_col = None
    for cand in ("powerball","pb","special","mega","lucky"):
        if cand in cols_l:
            special_col = lc_map[cand]; break
    return {"kind":"ball", "white_cols": white_cols, "special": special_col, "white_count": len(white_cols)}

def _counts_scores(vals: pd.Series, up_to: int, start_at_one: bool = True):
    counts = vals.value_counts().astype(float)
    lo = 1 if start_at_one else 0
    for i in range(lo, up_to + 1):
        if i not in counts.index:
            counts.loc[i] = 0.0
    counts = counts.sort_index()
    denom = (counts.max() - counts.min()) or 1.0
    return ((counts - counts.min()) / denom).to_dict()

def _prepare_pick3(df: pd.DataFrame):
    cols_l = [c.lower() for c in df.columns]
    if all(c in cols_l for c in ["n1","n2","n3"]):
        def col(name): return df[[c for c in df.columns if c.lower()==name][0]]
        d1 = _series_int(col("n1")).clip(0, 9)
        d2 = _series_int(col("n2")).clip(0, 9)
        d3 = _series_int(col("n3")).clip(0, 9)
    elif "digits" in cols_l:
        dcol = df[[c for c in df.columns if c.lower()=="digits"][0]].astype(str).str.replace(r"[^0-9]", "", regex=True)
        dcol = dcol.str.zfill(3).str[-3:]
        d1 = pd.to_numeric(dcol.str[0], errors="coerce").dropna().astype(int).clip(0,9)
        d2 = pd.to_numeric(dcol.str[1], errors="coerce").dropna().astype(int).clip(0,9)
        d3 = pd.to_numeric(dcol.str[2], errors="coerce").dropna().astype(int).clip(0,9)
    else:
        return {"ok": False, "note": "no digits columns"}
    return {"ok": True, "scores": {
        "d1": _counts_scores(d1, 9, start_at_one=False),
        "d2": _counts_scores(d2, 9, start_at_one=False),
        "d3": _counts_scores(d3, 9, start_at_one=False),
    }}

def train_frequency_model(game: str):
    df = _read_cache(game)
    if df.empty:
        return {"ok": False, "note": "no cached history"}

    if game == "pick3":
        prep = _prepare_pick3(df)
        if not prep.get("ok"):
            return {"ok": False, "note": prep.get("note", "pick3 prep failed")}
        model = {"game": "pick3", "type": "pick3", "scores": prep["scores"]}
        (MODELS / f"{game}_model.json").write_text(pd.Series(model).to_json(), encoding="utf-8")
        return {"ok": True, "note": "trained frequency model (pick3)", "rows": len(df)}

    sch = _detect_schema(df)
    whites = [c for c in sch["white_cols"] if c in df.columns]
    if not whites:
        return {"ok": False, "note": "no white columns detected"}

    white_max_by_game = {"cash5": 32, "colorado": 40, "powerball": 69, "megamillions": 70, "luckyforlife": 48}
    white_max = white_max_by_game.get(game, max(10, len(whites)*15))

    white_series = pd.concat([_series_int(df[c]) for c in whites], ignore_index=True)
    white_scores = _counts_scores(white_series, int(white_max), start_at_one=True)

    # Specials (clamped to canonical range)
    special_col = sch.get("special")
    special_max = CANON_SPECIAL_MAX.get(game)
    special_scores = None
    if special_col and special_max:
        sp = pd.to_numeric(df[special_col], errors="coerce").dropna().astype(int)
        sp = sp[(sp >= 1) & (sp <= int(special_max))]
        if not sp.empty:
            special_scores = _counts_scores(sp, int(special_max), start_at_one=True)

    model = {
        "game": game,
        "type": sch["kind"],
        "white_cols": whites,
        "white_count": int(sch["white_count"]),
        "white_max": int(white_max),
        "white_scores": white_scores,
        "special_col": special_col,
        "special_max": int(special_max) if special_max else None,
        "special_scores": special_scores,
    }
    (MODELS / f"{game}_model.json").write_text(pd.Series(model).to_json(), encoding="utf-8")
    return {"ok": True, "note": f"trained frequency model ({game})", "rows": len(df)}

def train_all():
    return {g: train_frequency_model(g) for g in GAME_TO_CACHE.keys()}
