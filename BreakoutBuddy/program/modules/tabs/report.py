# program/modules/tabs/report.py
from __future__ import annotations

from pathlib import Path
from typing import Any
import os
import pandas as pd  # type: ignore
import streamlit as st

APP_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("BREAKOUTBUDDY_DATA", APP_ROOT / "Data")).expanduser().resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _load_df() -> pd.DataFrame:
    for nm in ("ranked_latest.csv","explore_snapshot_latest.csv","ranked.csv","snapshot.csv"):
        p = DATA_DIR / nm
        if p.exists():
            try:
                return pd.read_csv(p)
            except Exception:
                pass
    return pd.DataFrame()

def _render(df: pd.DataFrame) -> None:
    # Safety casts
    for col in ("ChangePct","RVOL","RSI4","RelSPY"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    tabs = st.tabs(["Top Gainers", "Top Losers", "High RVOL", "Overbought/Oversold", "Summary"])

    with tabs[0]:
        if "ChangePct" in df.columns:
            top = df.sort_values("ChangePct", ascending=False).head(50)
            st.dataframe(top, use_container_width=True, hide_index=True)
        else:
            st.info("ChangePct not available.")

    with tabs[1]:
        if "ChangePct" in df.columns:
            bot = df.sort_values("ChangePct", ascending=True).head(50)
            st.dataframe(bot, use_container_width=True, hide_index=True)
        else:
            st.info("ChangePct not available.")

    with tabs[2]:
        if "RVOL" in df.columns:
            hi = df[df["RVOL"] >= 1.5].sort_values("RVOL", ascending=False).head(100)
            st.dataframe(hi, use_container_width=True, hide_index=True)
        else:
            st.info("RVOL not available.")

    with tabs[3]:
        if "RSI4" in df.columns:
            overbought = df[df["RSI4"] >= 75].sort_values("RSI4", ascending=False).head(100)
            oversold = df[df["RSI4"] <= 30].sort_values("RSI4", ascending=True).head(100)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Overbought (RSI4 ≥ 75)**")
                st.dataframe(overbought, use_container_width=True, hide_index=True)
            with col2:
                st.markdown("**Oversold (RSI4 ≤ 30)**")
                st.dataframe(oversold, use_container_width=True, hide_index=True)
        else:
            st.info("RSI4 not available.")

    with tabs[4]:
        st.markdown("**Snapshot Summary**")
        cols = [c for c in ("Ticker","ChangePct","RVOL","RSI4","RelSPY") if c in df.columns]
        st.write(f"Columns present: {', '.join(cols) or '(none)'}")
        st.write(f"Rows: {len(df)}")
        if "ChangePct" in df.columns:
            st.write(f"Avg ChangePct: {df['ChangePct'].mean():.3f}%")
        if "RVOL" in df.columns:
            st.write(f"Avg RVOL: {df['RVOL'].mean():.3f}")
        if "RSI4" in df.columns:
            st.write(f"Median RSI4: {df['RSI4'].median():.3f}")
        if "RelSPY" in df.columns:
            st.write(f"Avg RelSPY: {df['RelSPY'].mean():.3f}")

def render_report_tab(*, settings: Any = None) -> None:
    st.subheader("Reports")
    df = _load_df()
    if df is None or df.empty:
        st.info("No data to report on. Refresh from Dashboard/Explore first.")
        return
    _render(df)

# Alias for alternate wiring:
def render_reports_tab(*, settings: Any = None) -> None:
    render_report_tab(settings=settings)

# Generic name some apps use:
def render(*, settings: Any = None) -> None:
    render_report_tab(settings=settings)
