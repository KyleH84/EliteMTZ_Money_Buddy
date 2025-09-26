from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import pandas as pd
from ._common import _load_game_df

def frequency_analysis(df_or_path=None) -> dict:
    df = _load_game_df(df_or_path)
    whites = [c for c in df.columns if str(c).lower().startswith(("n","w","white","ball"))]
    specials = [c for c in df.columns if str(c).lower().startswith(("s","special"))]
    wc, sc = {}, {}
    for c in whites:
        for v in pd.to_numeric(df[c], errors="coerce").dropna().astype(int):
            wc[v] = wc.get(v,0)+1
    for c in specials:
        for v in pd.to_numeric(df[c], errors="coerce").dropna().astype(int):
            sc[v] = sc.get(v,0)+1
    return {"white_counts": dict(sorted(wc.items())), "special_counts": dict(sorted(sc.items()))}
