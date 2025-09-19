
from __future__ import annotations
import streamlit as st
import pandas as pd

# Try to import our new helpers; fall back gracefully if unavailable.
try:
    from modules.explain import explain_for_row
except Exception:
    explain_for_row = None  # type: ignore

try:
    from modules.services.augment_csv import augment_ranked_csv
except Exception:
    augment_ranked_csv = None  # type: ignore

def _add_quick_cols(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if explain_for_row is None:
        return df
    if "QuickWhy" in df.columns and "RiskBadge" in df.columns:
        return df  # already present
    exps = df.apply(lambda r: explain_for_row(r.to_dict()), axis=1)
    df["QuickWhy"] = [e.get("quick","") for e in exps]
    df["RiskBadge"] = [e.get("risk_badge","") for e in exps]
    return df

def render_dashboard_table(ranked_csv_path: str | None, df: pd.DataFrame | None) -> pd.DataFrame:
    "Call this from your existing dashboard tab after you load ranked data."
    if df is None and ranked_csv_path:
        try:
            if augment_ranked_csv:
                df = augment_ranked_csv(ranked_csv_path)
            else:
                df = pd.read_csv(ranked_csv_path)
        except Exception:
            df = pd.read_csv(ranked_csv_path) if ranked_csv_path else df
    if df is not None:
        df = _add_quick_cols(df)
        # Order columns if present
        cols = [c for c in ["Ticker","Open","High","Low","Close","Volume","Combined","P_up","Risk","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint","ChangePct","QuickWhy","RiskBadge"] if c in df.columns]
        df = df[cols + [c for c in df.columns if c not in cols]]
        st.dataframe(df, width="stretch")
    return df
