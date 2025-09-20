from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import pandas as pd
from .explain import explain_scan, alpha_density

def _df_to_markdown(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "_No rows_"
    cols = list(df.columns)
    lines = []
    # header
    lines.append("| " + " | ".join(str(c) for c in cols) + " |")
    lines.append("| " + " | ".join("---" for _ in cols) + " |")
    # rows
    for _, row in df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if isinstance(v, float):
                vals.append(f"{v:.3f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)

def build_daily_markdown(scored_df: pd.DataFrame) -> str:
    md = ["# BreakoutBuddy Daily Report"]
    md.append("## Top Picks (Why These)")
    md.append("")
    md.append("```\n" + explain_scan(scored_df, top_n=10) + "\n```")
    md.append("")
    md.append("## Alpha Density by Price Bucket")
    md.append("")
    ad = alpha_density(scored_df)
    md.append(_df_to_markdown(ad))
    md.append("")
    return "\n".join(md)
