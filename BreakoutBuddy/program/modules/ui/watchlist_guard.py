from __future__ import annotations
import pandas as pd
import streamlit as st

REQUIRED_COL_DEFAULTS = {
    "Ticker": "",
    "P_up": 0.55,
    "RelSPY": 0.0,
    "RVOL": 1.0,
    "Combined": 0.0,
}

def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Ensures required columns exist to avoid KeyError explosions
    if df is None:
        return pd.DataFrame({k: [v] for k, v in REQUIRED_COL_DEFAULTS.items()})
    for col, default in REQUIRED_COL_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default
    return df

def warn_if_constant(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        return
    const = []
    for c in ["P_up", "RelSPY", "RVOL", "Combined"]:
        if c in df.columns and df[c].nunique(dropna=False) <= 1:
            const.append(c)
    if const:
        st.info("Neutral defaults detected (demo mode or no fresh data). "
                "Toggle demo off in Admin → Feature Flags or refresh caches.")
