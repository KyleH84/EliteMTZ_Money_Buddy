
from __future__ import annotations
from pathlib import Path
from typing import List
import pandas as pd

EXPECTED = {
    "cached_powerball_data.csv":  {"cols": ["draw_date","white1","white2","white3","white4","white5","special"]},
    "cached_megamillions_data.csv":{"cols": ["draw_date","white1","white2","white3","white4","white5","special"]},
    "cached_luckyforlife_data.csv":{"cols": ["draw_date","white1","white2","white3","white4","white5","special"]},
    "cached_colorado_lottery_data.csv":{"cols": ["draw_date","n1","n2","n3","n4","n5","n6"]},
    "cached_cash5_data.csv":      {"cols": ["draw_date","n1","n2","n3","n4","n5"]},
    "cached_pick3_data.csv":      {"cols": ["draw_date","n1","n2","n3","d1","d2","d3"]},
}

def _coerce_dates(df: pd.DataFrame) -> pd.DataFrame:
    if "draw_date" in df.columns:
        df["draw_date"] = pd.to_datetime(df["draw_date"], errors="coerce").dt.date.astype(str)
    return df

def _ensure_pick3_dcols(df: pd.DataFrame) -> pd.DataFrame:
    if all(c in df.columns for c in ("n1","n2","n3")):
        for i in (1,2,3):
            d = f"d{i}"
            if d not in df.columns:
                df[d] = df[f"n{i}"]
    return df

def _normalize_pbmm_lfl(df: pd.DataFrame) -> pd.DataFrame:
    if "special" not in df.columns:
        for cand in ("powerball","mega_ball","megaball","lucky_ball","special_ball","bonus"):
            if cand in df.columns:
                df["special"] = df[cand]
                break
    return df

def _reorder(df: pd.DataFrame, need: List[str]) -> pd.DataFrame:
    out = pd.DataFrame({c: df[c] if c in df.columns else pd.NA for c in need})
    return out

def check_and_fix_caches(data_dir: Path) -> List[str]:
    msgs: List[str] = []
    for fname, info in EXPECTED.items():
        p = data_dir / fname
        need = info["cols"]
        if not p.exists():
            msgs.append(f"{fname}: missing (will be created by backfill).")
            continue
        try:
            df = pd.read_csv(p)
        except Exception as e:
            msgs.append(f"{fname}: read error: {e}")
            continue

        df = _coerce_dates(df)
        if "powerball" in fname or "megamillions" in fname or "luckyforlife" in fname:
            df = _normalize_pbmm_lfl(df)
        if "pick3" in fname:
            df = _ensure_pick3_dcols(df)

        out = _reorder(df, need)
        try:
            out.to_csv(p, index=False)
            msgs.append(f"{fname}: schema OK ({len(out)} rows).")
        except Exception as e:
            msgs.append(f"{fname}: write error: {e}")
    return msgs
