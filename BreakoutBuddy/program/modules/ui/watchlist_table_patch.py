
from __future__ import annotations
import streamlit as st
import pandas as pd

try:
    from modules.explain import explain_for_row
except Exception:
    explain_for_row = None  # type: ignore

def _add_quick_cols(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or explain_for_row is None:
        return df
    if "QuickWhy" in df.columns and "RiskBadge" in df.columns:
        return df
    exps = df.apply(lambda r: explain_for_row(r.to_dict()), axis=1)
    df["QuickWhy"] = [e.get("quick","") for e in exps]
    df["RiskBadge"] = [e.get("risk_badge","") for e in exps]
    return df

def render_watchlist_table(df: pd.DataFrame) -> pd.DataFrame:
    df = _add_quick_cols(df)
    cols = [c for c in ["Ticker","Open","High","Low","Close","Volume","ChangePct","P_up","Risk","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint","QuickWhy","RiskBadge"] if c in df.columns]
    df = df[cols + [c for c in df.columns if c not in cols]]
    st.dataframe(df, width="stretch")
    return df
