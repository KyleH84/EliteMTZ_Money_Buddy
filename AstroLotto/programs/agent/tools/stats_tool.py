from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import pandas as pd, numpy as np
from ._common import _load_game_df

def statistical_summary(df_or_path=None) -> dict:
    df = _load_game_df(df_or_path)
    out = {}
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        out[c] = {"mean": float(s.mean()), "std": float(s.std(ddof=1))}
    return out
