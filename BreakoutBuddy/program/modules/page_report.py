from pathlib import Path

# ---------- Strict per-app Data/Extras resolver (BreakoutBuddy) ----------
from pathlib import Path
import os, sys
BB_HERE     = Path(__file__).resolve()
BB_APP_ROOT = BB_HERE.parents[1]   # .../BreakoutBuddy

def _bb_cloud_roots():
    h = Path.home()
    return [
        h / "OneDrive",
        h / "OneDrive - Personal",
        h / "OneDrive - Wagstaff Law Firm",
        h / "Dropbox",
        h / "Google Drive",
        h / "Library" / "CloudStorage" / "OneDrive",
        h / "Library" / "CloudStorage" / "Dropbox",
        h / "Library" / "CloudStorage" / "GoogleDrive",
    ]

def _bb_first_existing(paths):
    for p in paths:
        try:
            p2 = Path(p).expanduser().resolve()
            if p2.exists():
                return p2
        except Exception:
            pass
    return None

def bb_resolve_dir(preferred_env_var: str, fallback_name: str):
    """
    Strict per-app order (NO repo-level fallback):
      1) Env var (abs or relative)
      2) BB_APP_ROOT/<name>
      3) CWD/<name>
      4) Cloud roots: <BreakoutBuddy>/<name>
      5) Create BB_APP_ROOT/<name>
    """
    envv = os.environ.get(preferred_env_var, "").strip()
    if envv:
        cand = (Path(envv) if os.path.isabs(envv) else (Path.cwd() / envv))
        if cand.exists():
            return cand.resolve()

    hit = _bb_first_existing([BB_APP_ROOT / fallback_name, Path.cwd() / fallback_name])
    if hit:
        return hit

    cands = []
    for root in _bb_cloud_roots():
        cands += [
            root / BB_APP_ROOT.name / fallback_name,
            root / "Projects" / BB_APP_ROOT.name / fallback_name,
        ]
    hit = _bb_first_existing(cands)
    if hit:
        return hit

    target = (BB_APP_ROOT / fallback_name).resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target

BB_DATA   = bb_resolve_dir("BREAKOUTBUDDY_DATA",   "Data")
BB_EXTRAS = bb_resolve_dir("BREAKOUTBUDDY_EXTRAS", "extras")

bb_extras_src = (BB_EXTRAS / "src")
if bb_extras_src.exists() and str(bb_extras_src) not in sys.path:
    sys.path.insert(0, str(bb_extras_src))
# ---------- end resolver ----------

# page_report_bb.py
import streamlit as st
import pandas as pd
import numpy as np
import io, os, json, time

st.set_page_config(page_title="BreakoutBuddy: Report", layout="wide")
st.title("BreakoutBuddy ▸ Report")
st.caption("Build a quick, shareable snapshot report. Point to a snapshot CSV (or paste a table).")

snap_csv = st.text_input("Snapshot CSV (exported ranked table)", value=str(BB_DATA / 'bb_snapshot.csv'))
top_n = st.number_input("Top N", value=20, min_value=5, max_value=200, step=5)
include_watchlist = st.checkbox("Include watchlist evaluation", value=True)
wl_csv = str(BB_DATA / 'watchlist.csv')

def load_df(path):
    if not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None

df = load_df(snap_csv)
if df is None:
    st.warning("No snapshot found. Export a ranked table to CSV from the dashboard and point to it here (e.g., Data/bb_snapshot.csv).")
    st.stop()

# Basic normalization
if "Ticker" not in df.columns and "ticker" in df.columns:
    df.rename(columns={"ticker":"Ticker"}, inplace=True)
if "Combined" not in df.columns and "FinalScore" in df.columns:
    df["Combined"] = df["FinalScore"]

# Slice top
top = df.sort_values("Combined", ascending=False).head(int(top_n)).copy()
cols = [c for c in ["Ticker","Combined","HeuristicScore","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint","ChangePct","Why"] if c in top.columns]

st.subheader("Top list preview")
st.dataframe(top[cols], width="stretch", height=360)

# Regime (if present)
regime_fields = [c for c in ["spy20d_trend","spy20d_vol","ma200_slope5","vix_percentile"] if c in df.columns]
regime_line = ", ".join([f"{c}={df[c].iloc[0]}" for c in regime_fields]) if regime_fields else "n/a"

# Watchlist evaluation
wl = None
if include_watchlist and os.path.exists(wl_csv):
    try:
        wl = pd.read_csv(wl_csv)
        wl_tickers = wl["Ticker"].astype(str).tolist()
        miss = [t for t in wl_tickers if t not in df["Ticker"].astype(str).tolist()]
        have = [t for t in wl_tickers if t in df["Ticker"].astype(str).tolist()]
        st.subheader("Watchlist coverage")
        st.write(f"Tickers in snapshot: {len(have)} / {len(wl_tickers)}")
        if have:
            st.dataframe(df[df["Ticker"].astype(str).isin(have)][cols], width="stretch", height=200)
        if miss:
            st.caption("Missing from snapshot: " + ", ".join(miss))
    except Exception:
        st.warning("Could not read watchlist.csv; skipping.")

# Build markdown report
def build_md():
    lines = []
    lines += ["# BreakoutBuddy — Snapshot Report", ""]
    lines += [f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    lines += [f"Universe size: {len(df)}"]
    lines += [f"Regime: {regime_line}", ""]
    lines += ["## Top list", ""]
    lines += [top[cols].to_markdown(index=False)]
    if include_watchlist and wl is not None:
        lines += ["", "## Watchlist in snapshot", ""]
        if have:
            lines += [df[df["Ticker"].astype(str).isin(have)][cols].to_markdown(index=False)]
        else:
            lines += ["(No watchlist tickers present.)"]
    return "\n".join(lines)

md = build_md()
st.subheader("Report (Markdown)")
st.code(md, language="markdown")

# Download as file
b = md.encode("utf-8")
st.download_button("Download report.md", b, file_name="bb_report.md", mime="text/markdown")
