
from __future__ import annotations
import streamlit as st
from pathlib import Path

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
