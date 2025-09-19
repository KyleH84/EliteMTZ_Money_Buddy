from __future__ import annotations
from typing import Dict, List, Tuple
import pandas as pd

WHITE_RANGES: Dict[str, Tuple[int,int,int]] = {
    "powerball": (1, 69, 5),
    "megamillions": (1, 70, 5),
    "luckyforlife": (1, 48, 5),
    "colorado": (1, 40, 6),
    "cash5": (1, 32, 5),
    "pick3": (0, 9, 3),
}
SPECIAL_RANGES: Dict[str, Tuple[int,int]] = {
    "powerball": (1, 26),
    "megamillions": (1, 25),
    "luckyforlife": (1, 18),
}

def detect_white_columns(df: pd.DataFrame) -> List[str]:
    cols = [c for c in df.columns if c.lower().startswith("white")]
    if cols:
        return sorted(cols, key=lambda x: int("".join([d for d in x if d.isdigit()]) or "0"))
    fall = [f"n{i}" for i in range(1,7) if f"n{i}" in df.columns]
    return fall

def long_short_blend(df: pd.DataFrame, game: str, short_days: int = 30, alpha: float = 0.3) -> Dict[int, float]:
    lo, hi, _ = WHITE_RANGES[game]
    whites = detect_white_columns(df)
    if not whites:
        return {i: 1.0 for i in range(lo, hi+1)}
    series_all = [pd.to_numeric(df[c], errors="coerce") for c in whites]
    all_vals = pd.concat(series_all, axis=0).dropna().astype(int)
    long_counts = all_vals.value_counts().to_dict()
    if "draw_date" in df.columns:
        try:
            cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=short_days)
            dfw = df[pd.to_datetime(df["draw_date"], errors="coerce") >= cutoff]
        except Exception:
            dfw = df.tail(50)
    else:
        dfw = df.tail(50)
    series_short = [pd.to_numeric(dfw[c], errors="coerce") for c in whites]
    short_vals = pd.concat(series_short, axis=0).dropna().astype(int)
    short_counts = short_vals.value_counts().to_dict()
    out: Dict[int, float] = {}
    total_long = sum(long_counts.values()) or 1
    total_short = sum(short_counts.values()) or 1
    for i in range(lo, hi+1):
        p_long = long_counts.get(i, 0) / total_long
        p_short = short_counts.get(i, 0) / total_short
        out[i] = (1 - alpha) * p_long + alpha * p_short
    return out

def gap_overdue_bonus(df: pd.DataFrame, game: str, strength: float = 0.2) -> Dict[int, float]:
    lo, hi, _ = WHITE_RANGES[game]
    whites = detect_white_columns(df)
    if not whites:
        return {i: 1.0 for i in range(lo, hi+1)}
    df2 = df.copy()
    if "draw_date" in df2.columns:
        df2 = df2.sort_values(pd.to_datetime(df2["draw_date"], errors="coerce"))
    order = df2.index.tolist()
    seen_idx: Dict[int, int] = {}
    for idx, row in df2.iterrows():
        for c in whites:
            try:
                n = int(row[c])
                seen_idx[n] = order.index(idx)
            except Exception:
                continue
    last_index = len(order) - 1
    total_draws = len(df2)
    unique = max(1, len(seen_idx))
    expected = max(1.0, total_draws / unique)
    out = {}
    for i in range(lo, hi+1):
        last_seen = seen_idx.get(i, -1)
        gap = (last_index - last_seen)
        ratio = gap / expected if expected else 1.0
        out[i] = 1.0 + strength * (ratio - 1.0) if ratio > 1 else 1.0
    return out
