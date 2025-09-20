from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import pandas as pd
import plotly.express as px
from ._common import _load_game_df

def frequency_chart(df_or_path=None, width=900, height=420):
    df = _load_game_df(df_or_path)
    whites = [c for c in df.columns if str(c).lower().startswith(("n","w","white","ball"))]
    if not whites: return None
    counts = {}
    for c in whites:
        for v in pd.to_numeric(df[c], errors="coerce").dropna().astype(int):
            counts[v] = counts.get(v,0)+1
    xs = sorted(counts); ys = [counts[x] for x in xs]
    fig = px.bar(x=xs, y=ys, labels={"x":"Number","y":"Count"}, title="White Number Frequency")
    fig.update_layout(width=width, height=height)
    return fig
