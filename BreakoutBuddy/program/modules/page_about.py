# page_about_bb.py
import streamlit as st

st.set_page_config(page_title="BreakoutBuddy: About", layout="wide")
st.title("BreakoutBuddy ▸ About")
st.info("See the **Glossary** page for definitions of RSI, RVOL, κ, Δt/Δt₀, Δt_K, and more.")

st.markdown("""
**What is BreakoutBuddy?**  
BreakoutBuddy is a momentum/breakout assistant. It ranks tickers by a **Combined** score derived from a baseline probability (**P_up**) and then adjusts for regime and crowd/retail risks. It supports simple NL filters, quick backtests, and now an optional **temporal helper** that nudges scores slightly toward the forecast time window.

### Key features
- **Ranking**: Computes `P_up` and a **Combined** score for each symbol.
- **Filters**: Natural‑language filters (e.g., `rsi2<5 and price<20 and rel>0`).
- **Backtest**: Quick RSI(2) test over ~2 years to sanity‑check settings.
- **Temporal helper (optional)**: Kozyrev‑style correction using **κ**, **Δt₀**, **Δt**, and **ε** with a small time‑sensitivity heuristic (∂score/∂t).
- **Autotune κ**: A dedicated page scans κ vs your outcomes and suggests a data‑driven value (min logloss / max AUC / min MSE).
- **Logging**: Each run appends to `Data/bb_temporal_logs.csv` for later analysis and tuning.

### How the temporal helper works
- We estimate a lightweight **∂score/∂t** from features like RelSPY, RVOL, RSI(4), and ChangePct.
- We compute a Kozyrev shift **Δt_K = κ · h · (1/Δt − 1/Δt₀)**.
- New score ≈ **score + (∂score/∂t) · Δt_K**, clamped back to \[0,1\].
- You can disable it or set sensitivity to zero if you want baseline behavior.

### Autotuning κ
1. Let the app log some runs with varied κ (including 0) → `Data/bb_temporal_logs.csv`.
2. Prepare outcomes → `Data/bb_outcomes.csv` with columns: `run_ts, ticker, label` (0/1 works great).
3. Open **Autotune κ** page. Pick the metric: **logloss** (default), **auc**, or **mse**.
4. Run the scan. Use one of the buttons:
   - **Use best κ now (this session)** → immediate test without restart.
   - **Save best κ to config** → writes `extras/bb_config.json`.
   - **Reload κ from config** → pulls saved κ into session.

### File layout (typical)
```
BreakoutBuddy/
├─ app_main.py
├─ modules/
│  ├─ __init__.py
│  ├─ temporal_agent.py
│  └─ meta_temporal_ensemble.py
├─ program/
│  └─ modules/
│     ├─ glossary.py
│     └─ page_autotune_bb.py
├─ extras/
│  └─ bb_config.json
└─ Data/
   ├─ breakoutbuddy.duckdb
   ├─ bb_temporal_logs.csv
   └─ bb_outcomes.csv
```

### Safety & sanity
- This tool is **experimental**. It’s designed for exploration and education, not guaranteed predictions.
- Start with small κ and short horizons, validate with the autotune page, and check that your score deltas make sense.
- Always keep a record of parameter changes; the CSV logs already help with that.
""")
