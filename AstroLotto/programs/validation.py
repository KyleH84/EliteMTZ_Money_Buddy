# utilities/validation.py - Patch 4 (v1.0)
# Walk-forward backtest utilities.
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple

def _date_col(df: pd.DataFrame) -> Optional[str]:
    for c in ("draw_date","date","Date"):
        if c in df.columns: return c
    return None

def _extract_set(row, white_cols: List[str], special_col: Optional[str]):
    whites = set()
    for c in white_cols:
        if c in row and pd.notna(row[c]):
            try:
                whites.add(int(row[c]))
            except Exception:
                pass
    special = None
    if special_col and special_col in row and pd.notna(row[special_col]):
        try: special = int(row[special_col])
        except Exception: special = None
    return whites, special

def walkforward_hits(
    df: pd.DataFrame,
    white_cols: List[str],
    special_col: Optional[str],
    window_days: int = 730,
    horizon_days: int = 7,
    n_tickets: int = 5,
    picks_func=None,
    game: Optional[str] = None,
) -> Dict[str, float]:
    dc = _date_col(df)
    if dc is None: return {"n_periods": 0}
    df = df.sort_values(dc).reset_index(drop=True)
    first = pd.to_datetime(df[dc].min()); last = pd.to_datetime(df[dc].max())
    if len(df) < 50: return {"n_periods": 0}

    periods = 0
    any_white = 0
    all_white = 0
    special_hit = 0
    draws_considered = 0

    cur = first + pd.Timedelta(days=window_days)
    while cur + pd.Timedelta(days=horizon_days) <= last:
        train = df[(pd.to_datetime(df[dc]) < cur) & (pd.to_datetime(df[dc]) >= cur - pd.Timedelta(days=window_days))]
        test = df[(pd.to_datetime(df[dc]) >= cur) & (pd.to_datetime(df[dc]) < cur + pd.Timedelta(days=horizon_days))]
        if train.empty or test.empty:
            cur += pd.Timedelta(days=horizon_days); continue

        tickets = picks_func(cur, train) if picks_func else []
        if not tickets:
            cur += pd.Timedelta(days=horizon_days); continue

        periods += 1
        for _, row in test.iterrows():
            wset, sp = _extract_set(row, white_cols, special_col)
            draws_considered += 1
            any_hit = False
            all_hit = False
            sp_hit = False
            for t in tickets:
                whites = set(t.get("white") or [])
                if whites & wset:
                    any_hit = True
                if whites and whites.issubset(wset):
                    all_hit = True
                if sp is not None and t.get("special") == sp:
                    sp_hit = True
            any_white += 1 if any_hit else 0
            all_white += 1 if all_hit else 0
            special_hit += 1 if sp_hit else 0

        cur += pd.Timedelta(days=horizon_days)

    if draws_considered == 0:
        return {"n_periods": periods, "draws": 0}

    return {
        "n_periods": periods,
        "draws": draws_considered,
        "pct_draws_with_any_white_hit": any_white / draws_considered,
        "pct_draws_with_all_whites_hit": all_white / draws_considered,
        "pct_draws_special_hit": (special_hit / draws_considered) if special_col else None,
    }
