from __future__ import annotations
import pandas as pd

def health_report(df) -> dict:
    rep = {}
    rep["n_rows"] = int(len(df))
    rep["null_frac"] = float(df.isna().mean().mean()) if len(df)>0 else 1.0
    rep["has_core_cols"] = all(c in df.columns for c in ["Close","RSI2","ConnorsRSI","RVOL"])
    level = "green"
    if rep["null_frac"] > 0.2: level = "yellow"
    if rep["null_frac"] > 0.4: level = "red"
    rep["level"] = level
    return rep
