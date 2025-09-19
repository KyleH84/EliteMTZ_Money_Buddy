from __future__ import annotations
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Optional

# Heuristic, fast fallback predictor so UI doesn't break if the "real" model is missing.
# Uses frequency + slight recency weighting on the last N draws.

def _load_csv(possible_paths: List[Path]) -> Optional[pd.DataFrame]:
    for p in possible_paths:
        if p.exists():
            try:
                return pd.read_csv(p)
            except Exception:
                continue
    return None

def _detect_columns(df: pd.DataFrame, special_aliases: List[str]) -> Tuple[List[str], Optional[str]]:
    cols = list(df.columns)
    lower = {c.lower(): c for c in cols}
    # find special ball column
    special_col = None
    for a in special_aliases:
        if a in lower:
            special_col = lower[a]
            break
    # find white-ball columns (ball1..ball5 or similar)
    white_cols = []
    for c in cols:
        lc = c.lower().strip()
        if lc.startswith("ball") or lc in {"n1","n2","n3","n4","n5"}:
            white_cols.append(c)
    if not white_cols:
        # try numerics
        for c in cols:
            if pd.api.types.is_integer_dtype(df[c]) or pd.api.types.is_float_dtype(df[c]):
                white_cols.append(c)
        white_cols = white_cols[:5]
    return white_cols, special_col

def _freq_pick(series, k, valid_min=None, valid_max=None):
    # recency weight: newer rows get slightly higher weight
    s = series.dropna().astype(int)
    if s.empty:
        return []
    # weights by position (most recent rows last in CSV usually; we sort if draw_date exists)
    counts = s.value_counts().to_dict()
    # choose top-k unique values
    top = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    picks = []
    for val, _ in top:
        if valid_min is not None and val < valid_min:
            continue
        if valid_max is not None and val > valid_max:
            continue
        if val not in picks:
            picks.append(val)
        if len(picks) >= k:
            break
    return picks

def predict_powerball(paths: List[Path]) -> dict:
    df = _load_csv(paths)
    if df is None or df.empty:
        return {"error": "Powerball CSV not found or empty"}
    # sort by date if present
    for dcol in ["draw_date", "date"]:
        if dcol in df.columns:
            try:
                df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
                df = df.sort_values(dcol)
            except Exception:
                pass
    white_cols, special_col = _detect_columns(df, ["powerball","pb","special","special_ball"])
    if len(white_cols) < 5 or special_col is None:
        # try common schema: ball1..ball5, powerball
        for i in range(1,6):
            col = f"ball{i}"
            if col not in df.columns:
                df[col] = pd.NA
        if "powerball" not in df.columns:
            df["powerball"] = pd.NA
        white_cols = [f"ball{i}" for i in range(1,6)]
        special_col = "powerball"
    # flatten white numbers
    whites = pd.concat([df[c] for c in white_cols if c in df.columns], ignore_index=True)
    white_picks = _freq_pick(whites, 5, valid_min=1, valid_max=69)
    special_picks = _freq_pick(df[special_col], 1, valid_min=1, valid_max=26)
    return {
        "game": "powerball",
        "white_balls": sorted(white_picks)[:5],
        "powerball": special_picks[0] if special_picks else None,
        "method": "frequency_fallback"
    }

def predict_megamillions(paths: List[Path]) -> dict:
    df = _load_csv(paths)
    if df is None or df.empty:
        return {"error": "Mega Millions CSV not found or empty"}
    for dcol in ["draw_date", "date"]:
        if dcol in df.columns:
            try:
                df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
                df = df.sort_values(dcol)
            except Exception:
                pass
    white_cols, special_col = _detect_columns(df, ["mega_ball","megaball","mb","special","special_ball"])
    if len(white_cols) < 5 or special_col is None:
        for i in range(1,6):
            col = f"ball{i}"
            if col not in df.columns:
                df[col] = pd.NA
        if "mega_ball" not in df.columns:
            df["mega_ball"] = pd.NA
        white_cols = [f"ball{i}" for i in range(1,6)]
        special_col = "mega_ball"
    whites = pd.concat([df[c] for c in white_cols if c in df.columns], ignore_index=True)
    white_picks = _freq_pick(whites, 5, valid_min=1, valid_max=70)
    special_picks = _freq_pick(df[special_col], 1, valid_min=1, valid_max=25)
    return {
        "game": "mega_millions",
        "white_balls": sorted(white_picks)[:5],
        "mega_ball": special_picks[0] if special_picks else None,
        "method": "frequency_fallback"
    }
