from __future__ import annotations

from pathlib import Path
import os
import streamlit as st
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)



# BreakoutBuddy Glossary
# This updates the original TERMS with temporal + scoring concepts.

TERMS = {
    # ── Momentum/volatility & ranking basics ──────────────────────────────
    "RSI": "Relative Strength Index: 0–100 momentum scale. Low = oversold; high = overbought.",
    "RSI2": "2‑day RSI: very short-term RSI used for quick mean‑reversion bounces.",
    "RSI4": "4‑day RSI: slightly slower short‑term RSI.",
    "ConnorsRSI": "Larry Connors composite (RSI(3), streak RSI(2), and 100‑day percentile of daily return). Lower = better for bounces.",
    "RelSPY": "Relative strength vs SPY: >0 means the stock outperformed SPY over the lookback.",
    "PctFrom200d": "Percent distance from 200‑day moving average. >0 = above long‑term trend.",
    "ATR": "Average True Range: typical daily range; a proxy for volatility.",
    "RVOL": "Relative Volume: today’s volume vs 20‑day average. 1.0 = normal; 2.0 = 2× normal.",
    "SqueezeHint": "Compression flag based on recent narrow ranges. 1 = compressed; can pop.",
    "CrowdRisk": "How crowded/obvious the setup looks (RVOL + near highs). Higher = more chase risk.",
    "RetailChaseRisk": "Proxy for retail chase (very hot RSI + high RVOL). Higher = more likely to fade.",
    "P_up": "Model probability the stock goes up (given current features).",
    "Combined": "The score BreakoutBuddy ranks by. Starts from P_up then applies bonuses/penalties (e.g., regime, crowd).",
    "FinalScore": "Legacy alias for the rank score; prefer 'Combined'.",
    "Universe size": "How many symbols to scan from a liquid preset list. Larger = slower.",
    "NL filters": "Natural‑language filters like: rsi2<5 and price<20 and rel>0. Aliases: price/close, rel=RelSPY, rvol, atr, crowd, retail, squeeze, pct200.",
    "Quick Backtest": "Runs a fast RSI(2)<5 test on your current universe over ~2y, labeling +3% within 5 days.",

    # ── Temporal helper (Kozyrev) ─────────────────────────────────────────
    "κ (kappa)": "Kozyrev coupling strength for temporal correction. Controls the magnitude of the time‑nudge.",
    "Δt₀ (dt0)": "Reference window (seconds). Baseline horizon used to anchor the time‑energy density.",
    "Δt (dt)": "Forecast window (seconds). Effective horizon you’re targeting (e.g., 30m, 2h, EOD).",
    "ε (epsilon)": "Finite‑difference step (in days) used to estimate time sensitivity (∂score/∂t).",
    "∂score/∂t": "Sensitivity of the score w.r.t. time. Heuristic in BB uses RelSPY, RVOL, RSI(4), and ChangePct.",
    "Δt_K (dt_K)": "Kozyrev time‑shift term: Δt_K = κ · h · (1/Δt − 1/Δt₀). The correction applies (∂score/∂t)·Δt_K.",
    "E_t / E_t0": "Time‑energy diagnostics proportional to h/Δt and h/Δt₀; logged for transparency.",

    # ── Logging & autotune ────────────────────────────────────────────────
    "bb_temporal_logs.csv": "One row per run/ticker with base/final scores, delta_K, dt_K, and κ settings.",
    "bb_outcomes.csv": "Your realized labels joined by (run_ts, ticker). Needed for autotuning.",
    "logloss": "Classification loss; lower is better. Autotune picks κ minimizing log‑loss.",
    "AUC": "Area under ROC; higher is better. Good for threshold‑free ranking quality.",
    "MSE": "Mean Squared Error; for regression‑style targets. Lower is better.",
    "Session κ": "When you click ‘Use best κ now’ on the autotune page, the value is stored in session and used immediately.",
    "Config κ": "Saved default in extras/bb_config.json. Loaded on app start, unless a session κ overrides it.",
}

def render_sidebar_help(st):
    with st.sidebar.expander("📘 Glossary / What do these mean?", expanded=False):
        for k, v in TERMS.items():
            st.markdown(f"**{k}** — {v}")