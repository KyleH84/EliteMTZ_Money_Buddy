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
    if df is None:
        return pd.DataFrame({k: [v] for k, v in REQUIRED_COL_DEFAULTS.items()})
    for col, default in REQUIRED_COL_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default
    return df

def require_column(df: pd.DataFrame, target: str, fallback_names=(), prefix: str | None = None, default=0.0) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame({target: [default]})
    if target in df.columns:
        return df
    lower = {c.lower(): c for c in df.columns}
    for name in (list(fallback_names) + [target]):
        c = lower.get(str(name).lower())
        if c:
            if c != target:
                df.rename(columns={c: target}, inplace=True)
            return df
    if prefix:
        for c in df.columns:
            if c.lower().startswith(prefix.lower()):
                df.rename(columns={c: target}, inplace=True)
                return df
    df[target] = default
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
