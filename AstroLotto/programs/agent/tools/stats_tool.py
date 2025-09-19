
from __future__ import annotations
import pandas as pd, numpy as np
from ._common import _load_game_df

def statistical_summary(df_or_path=None) -> dict:
    df = _load_game_df(df_or_path)
    out = {}
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        out[c] = {"mean": float(s.mean()), "std": float(s.std(ddof=1))}
    return out
