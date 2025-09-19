
from __future__ import annotations
import streamlit as st
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

def render_about_tab(**kwargs):
    st.header("About")
    d = _data_dir()
    st.write("**BreakoutBuddy — fast ranking, watchlist, agents, and reports.**")
    st.markdown(f"Data dir: `{d}`")

    with st.expander("Glossary (plain English)"):
        st.markdown('''
- **P_up** — model's tilt up (0–1). Quick confidence proxy.
- **Combined / Combined_base / Combined_with_agents** — composite scores; *with_agents* adds AgentBoost.
- **AgentBoost_exact** — lift from agents. ▲ large positive; ▼ negative.
- **RelSPY** — how the ticker performed vs SPY recently.
- **RVOL** — relative volume (1.5 = 50% above typical). Heat.
- **RSI4 / ConnorsRSI** — short-term momentum/overbought/oversold.
- **SqueezeHint** — simple proxy for compression/expansion setups.
- **Risk badge** — quick read (Low/Medium/High) from RVOL/RSI/move.
        ''')

    with st.expander("How it works (technical)"):
        st.markdown('''
1. **Enrich snapshot** — fetch OHLCV, compute features (P_up, RelSPY, RVOL, RSI4, ConnorsRSI, SqueezeHint).
2. **Rank** — form `Combined_base` then apply **agents** (technicals/pattern/volatility) → `Combined_with_agents`.
3. **Persist** — write `Data/ranked_latest.csv` and `Data/watchlist_snapshot_latest.csv` for instant page paint.
4. **Calibrate agents** — ridge-fit weights on your latest ranked CSV → `Data/agent_weights.json`.
5. **Explain** — per-row Quick Why + Pros/Cons; optionally augmented with your **local LLM (.gguf)**.
        ''')

    with st.expander("Tips"):
        st.markdown('''
- Keep **watchlist.csv** lean. Add/remove from Watchlist tab.
- If pages feel stale, Admin → **Calibrate + Re-rank now**.
- Point Admin → **Local LLMs** at your `.gguf` folder for nicer prose (no internet/keys).
        ''')
