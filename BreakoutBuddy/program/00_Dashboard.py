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

# 00_Dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import os, json, time

st.set_page_config(page_title="BreakoutBuddy: Dashboard", layout="wide")
st.title("BreakoutBuddy ▸ Dashboard")
st.caption("Ranked snapshot, quick analyze, scanner, explore, and watchlist. Uses CSV snapshots/logs so it's easy to swap in your pipeline.")

SNAP_PATH = str(BB_DATA / 'bb_snapshot.csv')
LOGS_PATH = str(BB_DATA / 'bb_temporal_logs.csv')
WL_PATH = str(BB_DATA / 'watchlist.csv')

def load_csv(path):
    if not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None

def save_watchlist(df):
    try:
        Path(WL_PATH).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(WL_PATH, index=False)
        return True
    except Exception:
        return False

def get_watchlist():
    if os.path.exists(WL_PATH):
        try:
            df = pd.read_csv(WL_PATH)
            if "Ticker" not in df.columns:
                df = pd.DataFrame({"Ticker":[]})
            return df
        except Exception:
            pass
    return pd.DataFrame({"Ticker":[]})

# --- Load snapshot ---
snap = load_csv(SNAP_PATH)
if snap is None or snap.empty:
    st.warning(f"No snapshot found at {SNAP_PATH}. Export your ranked table to this path or upload below.")
    up = st.file_uploader("Upload a snapshot CSV", type=["csv"])
    if up is not None:
        snap = pd.read_csv(up)
if snap is None or snap.empty:
    st.stop()

# Normalize basic columns
if "Ticker" not in snap.columns and "ticker" in snap.columns:
    snap.rename(columns={"ticker":"Ticker"}, inplace=True)
if "Combined" not in snap.columns and "FinalScore" in snap.columns:
    snap["Combined"] = snap["FinalScore"]

base_cols = ["Ticker","Combined","HeuristicScore","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint","ChangePct","Why"]
present_cols = [c for c in base_cols if c in snap.columns]

# --- Top table with quick actions ---
st.subheader("Top ranked")
top_n = st.number_input("Top N", value=50, min_value=5, max_value=500, step=5)
top = snap.sort_values("Combined", ascending=False).head(int(top_n)).copy()

col_tbl, col_actions = st.columns([3,1])
with col_tbl:
    st.dataframe(top[present_cols], width="stretch", height=380, hide_index=True)
with col_actions:
    st.write("Quick actions")
    for _, r in top.head(30).iterrows():
        tkr = str(r.get("Ticker",""))
        if st.button(f"🔍 {tkr}", key=f"an_{tkr}"):
            st.session_state["bb_analyze_ticker"] = tkr
        if st.button(f"➕ {tkr}", key=f"wl_{tkr}"):
            wl = get_watchlist()
            if tkr not in set(wl["Ticker"]):
                wl = wl._append({"Ticker": tkr}, ignore_index=True)
                if save_watchlist(wl):
                    st.toast(f"Added {tkr} to watchlist", icon="✅")

st.divider()

# --- Single Ticker Analyzer ---
st.subheader("Single Ticker Analyzer")
tkr = st.text_input("Ticker", value=st.session_state.get("bb_analyze_ticker",""), key="bb_analyze_ticker").strip().upper()
cA, cB, cC = st.columns([2,1,1])
with cA:
    analyze = st.button("Analyze")
with cB:
    add_wl = st.button("➕ Add to Watchlist")
with cC:
    remove_wl = st.button("🗑 Remove from Watchlist")

if add_wl and tkr:
    wl = get_watchlist()
    if tkr not in set(wl["Ticker"]):
        wl = wl._append({"Ticker": tkr}, ignore_index=True)
        save_watchlist(wl)
        st.success(f"Added {tkr} to watchlist")
if remove_wl and tkr:
    wl = get_watchlist()
    wl = wl[wl["Ticker"] != tkr]
    save_watchlist(wl)
    st.info(f"Removed {tkr} from watchlist")

if analyze and tkr:
    # Show latest snapshot row for ticker
    row = snap[snap["Ticker"].astype(str)==tkr]
    if row.empty:
        st.warning("Ticker not in snapshot. Generate a fresh snapshot or upload one that includes it.")
    else:
        st.write("Snapshot row:")
        st.dataframe(row[present_cols], width="stretch", hide_index=True)
        # If logs have detail, show last logged run
        logs = load_csv(LOGS_PATH)
        if logs is not None and not logs.empty:
            # normalize columns
            if "ticker" in logs.columns and "Ticker" not in logs.columns:
                logs.rename(columns={"ticker":"Ticker"}, inplace=True)
            sub = logs[logs["Ticker"].astype(str)==tkr]
            if not sub.empty:
                last = sub.sort_values("run_ts").tail(1)
                show = ["run_ts","Ticker","score_base","score_final","delta_y_K","dt_K","Et","Et0",
                        "RelSPY","RVOL","RSI4","ConnorsRSI","ChangePct","SqueezeHint","HeuristicScore","Combined"]
                show = [c for c in show if c in last.columns]
                st.write("Latest log row:")
                st.dataframe(last[show], width="stretch", hide_index=True)

st.divider()
# --- Scanner ---
st.subheader("Scanner")
metric = st.selectbox("Metric", ["Combined","HeuristicScore","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint","ChangePct"], index=0)
min_val = st.number_input("Min", value=float(snap[metric].min()) if metric in snap.columns else 0.0)
max_val = st.number_input("Max", value=float(snap[metric].max()) if metric in snap.columns else 1.0)
scan = snap.copy()
if metric in scan.columns:
    scan = scan[(scan[metric] >= min_val) & (scan[metric] <= max_val)]
st.dataframe(scan[present_cols], width="stretch", height=240, hide_index=True)

st.divider()
# --- Explore Snapshot ---
st.subheader("Explore Snapshot")
st.write(f"Rows: {len(snap)}")
try:
    cols = ["Combined","HeuristicScore","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint","ChangePct"]
    cols = [c for c in cols if c in snap.columns]
    st.write("Averages:", snap[cols].mean(numeric_only=True))
    st.write("Top 5 tickers:", ", ".join(snap.sort_values("Combined", ascending=False).head(5)["Ticker"].astype(str).tolist()))
except Exception:
    pass

st.divider()
# --- Watchlist ---
st.subheader("Watchlist")
wl = get_watchlist()
if wl.empty:
    st.caption("No tickers saved yet. Use ➕ buttons above or in Analyzer.")
else:
    st.dataframe(wl, width="stretch", height=160, hide_index=True)
    c1, c2 = st.columns([2,1])
    with c1:
        tsel = st.selectbox("Analyze from watchlist", wl["Ticker"].tolist())
    with c2:
        if st.button("Analyze selected", key="wl_analyze"):
            st.session_state["bb_analyze_ticker"] = tsel
            st.experimental_rerun()
