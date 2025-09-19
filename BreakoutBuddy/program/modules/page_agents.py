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

# page_agents_bb.py
import streamlit as st
import pandas as pd
import numpy as np
import os, json, time, math

st.set_page_config(page_title="BreakoutBuddy: Agents", layout="wide")
st.title("BreakoutBuddy ▸ Agents")
st.caption("Explainers, temporal what‑ifs, and multiverse sampling for a single ticker. Works off your logs CSV.")

# --- Inputs ---
logs_csv = st.text_input("Logs CSV (bb_temporal_logs.csv)", value=str(BB_DATA / 'bb_temporal_logs.csv'))
ticker = st.text_input("Ticker", value=st.session_state.get("bb_analyze_ticker","")).strip().upper()
col = st.columns(4)
with col[0]:
    kappa = st.number_input("κ (s/J)", value=0.0, format="%.6e")
with col[1]:
    dt_ref = st.number_input("Δt₀ (sec)", value=3600.0, step=600.0)
with col[2]:
    dt_win = st.number_input("Δt (sec)", value=3600.0, step=600.0)
with col[3]:
    multiverse = st.checkbox("Enable multiverse sampling", value=False)
mv_cols = st.columns(2)
with mv_cols[0]:
    mv_k = st.number_input("Universes (K)", value=7, min_value=1, max_value=51, step=2)
with mv_cols[1]:
    mv_eps = st.number_input("Sensitivity jitter (±%)", value=10.0, min_value=0.0, max_value=50.0, step=1.0)

st.divider()

# --- Load last observation for ticker from logs ---
def load_last_row(logs_csv, ticker):
    if not os.path.exists(logs_csv):
        return None
    try:
        d = pd.read_csv(logs_csv)
    except Exception:
        return None
    if "ticker" not in d.columns:
        # try uppercase
        cols_lower = {c.lower(): c for c in d.columns}
        if "ticker" in cols_lower:
            d.rename(columns={cols_lower["ticker"]:"ticker"}, inplace=True)
    d = d[d["ticker"].astype(str).str.upper() == ticker]
    if d.empty:
        return None
    d = d.sort_values("run_ts").tail(1)
    return d.iloc[0].to_dict()

row = load_last_row(logs_csv, ticker) if ticker else None

if not ticker:
    st.info("Enter a ticker to begin.")
    st.stop()

if row is None:
    st.warning(f"No log rows found for {ticker}. Run the main dashboard once so it logs bb_temporal_logs.csv.")
    st.stop()

st.subheader(f"Latest snapshot for {ticker}")
# Show basic fields if present
show_cols = ["run_ts","ticker","score_base","score_final","delta_y_K","dt_K","Et","Et0",
             "RelSPY","RVOL","RSI4","ConnorsRSI","ChangePct","SqueezeHint","HeuristicScore","Combined"]
view = {k: row.get(k) for k in show_cols if k in row}
st.json(view, expanded=False)

# --- Plain-English explainer agent ---
st.subheader("Agent: Plain‑English explainer")
bullets = []
def add(msg): bullets.append("• " + msg)
r = row
# Heuristic explanations
def _fmtFloat(x, d=3):
    try: return f"{float(x):.{d}f}"
    except Exception: return str(x)
if r.get("RelSPY") is not None:
    add(f"Relative strength vs SPY: {_fmtFloat(r['RelSPY'])} ({'stronger' if float(r['RelSPY'])>0 else 'weaker'} than SPY over lookback).")
if r.get("RVOL") is not None:
    add(f"Relative volume: {_fmtFloat(r['RVOL'],2)}× normal; higher suggests attention/liquidity.")
if r.get("RSI4") is not None:
    rsi4 = float(r["RSI4"])
    zone = "oversold" if rsi4<30 else ("overbought" if rsi4>70 else "neutral")
    add(f"RSI(4): {_fmtFloat(r['RSI4'],1)} ({zone}).")
if r.get("ConnorsRSI") is not None:
    crsi = float(r["ConnorsRSI"])
    zone = "oversold" if crsi<20 else ("overbought" if crsi>80 else "neutral")
    add(f"ConnorsRSI: {_fmtFloat(crsi,1)} ({zone}).")
if r.get("SqueezeHint") is not None:
    add(f"Squeeze hint: {_fmtFloat(r['SqueezeHint'],3)} (higher = more compressed).")
if r.get("ChangePct") is not None:
    add(f"Today change %: {_fmtFloat(r['ChangePct'],3)}.")
if r.get("score_final") is not None and r.get("score_base") is not None:
    add(f"Temporal nudge moved score from {_fmtFloat(r['score_base'])} → {_fmtFloat(r['score_final'])}.")
st.write("\n".join(bullets) if bullets else "No detailed features logged; only scores are available.")

# --- Temporal what‑if agent ---
st.subheader("Agent: Temporal what‑if")
# Estimate sensitivity from previous run if possible: d y / d tK ≈ delta_y_K / dt_K
dydt_est = None
if row.get("delta_y_K") is not None and row.get("dt_K") not in (None, 0, "0", 0.0):
    try:
        dydt_est = float(row["delta_y_K"]) / float(row["dt_K"])
    except Exception:
        dydt_est = None
base = float(row.get("score_base", row.get("score_final", 0.5)))
h = 6.62607015e-34  # Planck (J·s)
dtK = kappa * h * (1.0/max(dt_win,1e-6) - 1.0/max(dt_ref,1e-6))
if dydt_est is not None:
    y_proj = float(np.clip(base + dydt_est * dtK, 0.0, 1.0))
else:
    y_proj = base  # no change if we can't estimate sensitivity
cols = st.columns(3)
with cols[0]:
    st.metric("Base score", f"{base:.3f}")
with cols[1]:
    st.metric("Projected (κ, Δt₀, Δt)", f"{y_proj:.3f}")
with cols[2]:
    st.metric("Δt_K", f"{dtK:.3e}")

# --- Multiverse sampling agent ---
st.subheader("Agent: Multiverse sampler")
if not multiverse:
    st.caption("Turn on 'Enable multiverse sampling' to simulate jittered sensitivities and average.")
else:
    rng = np.random.default_rng(42)
    K = int(mv_k)
    eps = float(mv_eps) / 100.0
    sims = []
    for _ in range(K):
        if dydt_est is None:
            sims.append(base)
            continue
        jitter = 1.0 + rng.uniform(-eps, eps)
        y = float(np.clip(base + (dydt_est*jitter) * dtK, 0.0, 1.0))
        sims.append(y)
    st.write(f"K = {K}, jitter ±{mv_eps:.1f}%")
    st.write(pd.DataFrame({"y": sims}).describe())
    st.metric("Multiverse mean", f"{np.mean(sims):.3f}")

st.divider()
st.caption("Tip: Run the main dashboard to log fresh rows into bb_temporal_logs.csv, then come here to analyze a ticker.")
