
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from modules import explain as explain_mod

COLUMNS_ALL = ["Ticker","Open","High","Low","Close","Volume","Combined","P_up","Risk","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint","ChangePct","AgentBoost_exact","QuickWhy","RiskBadge"]

def _data_dir() -> Path:
    here = Path(__file__).resolve()
    for up in [here, *here.parents]:
        cand = up / "Data"
        if cand.is_dir():
            return cand
        if up.name == "program":
            cand2 = up.parent / "Data"
            if cand2.is_dir():
                return cand2
    fb = here.parent / "Data"
    fb.mkdir(parents=True, exist_ok=True)
    return fb

def _load_csv(name: str) -> tuple[pd.DataFrame, str]:
    p = _data_dir() / name
    if p.exists():
        try:
            df = pd.read_csv(p)
            ts = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            return df, ts
        except Exception:
            return pd.DataFrame(), ""
    return pd.DataFrame(), ""

def _lift_chip(v: float) -> str:
    try:
        x = float(v)
        if x > 5: return "▲"
        if x < -5: return "▼"
        return ""
    except Exception:
        return ""

def _ensure_explanations(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    qs = []; rb = []
    for _, row in df.iterrows():
        exp = explain_mod.explain_for_row(row, allow_local_llm=True)
        qs.append(exp.get("quick",""))
        rb.append(exp.get("risk_badge",""))
    out = df.copy()
    out["QuickWhy"] = qs
    out["RiskBadge"] = rb
    return out

def _order_cols(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in COLUMNS_ALL if c in df.columns]
    return df[cols] if cols else df

def render_dashboard_tab(*, settings=None, **kwargs):
    st.header("Dashboard")
    ranked, ts = _load_csv("ranked_latest.csv")
    if ranked.empty:
        st.info("No ranked data yet. Go to Admin and run a manual scan & rank once.")
        return

    st.sidebar.subheader("Filters")
    min_comb = st.sidebar.slider("Min Combined (with agents if present)", 0, 100, 0, 1)
    min_pup = st.sidebar.slider("Min P_up (%)", 0, 100, 0, 1)
    only_pos_rel = st.sidebar.checkbox("RelSPY > 0", value=False)

    df = ranked.copy()

    # Robust Combined_show derivation (avoid float.fillna crash)
    if "Combined_with_agents" in df.columns:
        base = pd.to_numeric(df["Combined_with_agents"], errors="coerce")
    elif "Combined" in df.columns:
        base = pd.to_numeric(df["Combined"], errors="coerce")
    elif "Combined_base" in df.columns:
        base = pd.to_numeric(df["Combined_base"], errors="coerce")
    else:
        base = pd.Series(0.0, index=df.index)
    df["Combined_show"] = base.fillna(0.0)

    # Filters
    df = df[df["Combined_show"] >= float(min_comb)]
    if "P_up" in df.columns:
        pup = pd.to_numeric(df["P_up"], errors="coerce").fillna(0.0) * 100.0
        df = df[pup >= float(min_pup)]
    if only_pos_rel and "RelSPY" in df.columns:
        df = df[pd.to_numeric(df["RelSPY"], errors="coerce").fillna(0.0) > 0.0]

    # Ensure agent columns
    if "AgentBoost_exact" not in df.columns or "Combined_with_agents" not in df.columns:
        try:
            from modules.services import agents_service as AS
            df = AS.enrich_scores(df)
        except Exception:
            if "AgentBoost_exact" not in df.columns:
                df["AgentBoost_exact"] = 0.0
            if "Combined_with_agents" not in df.columns:
                df["Combined_with_agents"] = df.get("Combined", 0.0)

    st.caption(f"Last ranked: {ts} • Universe: {len(df)} rows")
    df["Lift"] = df["AgentBoost_exact"].apply(_lift_chip)
    df = _ensure_explanations(df)

    view = _order_cols(df)
    st.dataframe(view, height=520, width='stretch')

    # Detail pane: pick a ticker
    if not df.empty and "Ticker" in df.columns:
        tickers = list(df["Ticker"].astype(str))
        sel = st.selectbox("Details for", options=tickers)
        if sel:
            row = df[df["Ticker"].astype(str) == sel].iloc[0].to_dict()
            exp = explain_mod.explain_for_row(row, allow_local_llm=True)
            st.markdown("### Why (detailed)")
            st.write(exp.get("detailed",""))
