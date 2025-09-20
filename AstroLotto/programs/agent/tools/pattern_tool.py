from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import pandas as pd, numpy as np
from ._common import _load_game_df

def pattern_detection(df_or_path=None) -> dict:
    df = _load_game_df(df_or_path)
    whites = [c for c in df.columns if str(c).lower().startswith(("n","w","white","ball"))]
    if not whites: return {"rows": len(df)}
    W = df[whites].apply(pd.to_numeric, errors="coerce").dropna()
    evens = int((W % 2 == 0).sum().sum())
    odds = int(W.size - (W % 2 == 0).sum().sum())
    sums = W.sum(axis=1)
    seq_rows = 0
    for _, row in W.iterrows():
        a = sorted(int(x) for x in row.values)
        if any(a[i+1]-a[i]==1 for i in range(len(a)-1)): seq_rows += 1
    return {"rows": len(W), "even_odd": {"even": evens, "odd": odds},
            "sum": {"mean": float(sums.mean()), "std": float(sums.std(ddof=1))},
            "rows_with_consecutive_pairs": int(seq_rows)}
