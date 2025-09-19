
from __future__ import annotations
import pandas as pd

def rank_now(enriched_df: pd.DataFrame) -> pd.DataFrame:
    df = enriched_df.copy()
    if "Combined" not in df.columns:
        pu = pd.to_numeric(df.get("P_up", 0.5), errors="coerce").fillna(0.5)
        rel = pd.to_numeric(df.get("RelSPY", 0.0), errors="coerce").fillna(0.0)
        rv  = pd.to_numeric(df.get("RVOL", 1.0), errors="coerce").fillna(1.0)
        df["Combined"] = (pu * 70.0 + rel * 10.0 + (rv - 1.0) * 20.0).clip(0, 100)
    try:
        from modules.services import agents_service as AS
        df = AS.enrich_scores(df)
    except Exception:
        pass
    sort_col = "Combined_with_agents" if "Combined_with_agents" in df.columns else "Combined"
    df = df.sort_values(by=[sort_col], ascending=False).reset_index(drop=True)
    return df
