# Program/utilities/heuristic_presets.py
from __future__ import annotations
from typing import List, Set, Dict, Tuple
import pandas as pd
import datetime as dt

def numbers_in_last_days(df: pd.DataFrame, white_cols: List[str], days: int = 30) -> Set[int]:
    if df is None or df.empty or not white_cols:
        return set()
    if "draw_date" in df.columns:
        try:
            cutoff = pd.Timestamp(dt.date.today() - dt.timedelta(days=days))
            sdf = df[pd.to_datetime(df["draw_date"], errors="coerce") >= cutoff]
        except Exception:
            sdf = df
    else:
        sdf = df.tail(10)
    s: Set[int] = set()
    for c in white_cols:
        if c in sdf.columns:
            try:
                vals = pd.to_numeric(sdf[c], errors="coerce").dropna().astype(int).tolist()
                s.update(vals)
            except Exception:
                continue
    return s

def passes_odd_even_game(game: str, nums: List[int]) -> bool:
    k = len(nums)
    odd = sum(1 for x in nums if x % 2 == 1)
    if game in ("powerball","megamillions","cash5","luckyforlife"):
        return odd in (2,3)  # 5-ball games
    if game == "colorado":  # Lotto+ (6 numbers)
        return odd == 3      # strict 3:3
    # pick3 not used here
    return True
