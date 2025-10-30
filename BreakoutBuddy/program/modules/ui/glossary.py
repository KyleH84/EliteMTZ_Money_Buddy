from __future__ import annotations
import streamlit as st

TERMS = [
    ("P_up", "Percent of up days over a recent lookback (default 20)."),
    ("RelSPY", "Security's 20-day return minus SPY's 20-day return."),
    ("RVOL", "Relative volume: latest volume divided by 20-day average volume."),
    ("RSI4", "4‑period Relative Strength Index."),
    ("ConnorsRSI", "Composite of short RSI, streak RSI, and 2‑day percent rank."),
    ("ATR", "Average True Range, volatility measure."),
    ("PctFrom200d", "Percent distance from 200‑day simple moving average."),
    ("SqueezeHint", "BB(20,2) inside Keltner(20,1.5) = 'Squeeze', else 'Off'."),
    ("RiskBadge", "High/Medium/Low Volume classification from RVOL."),
]

def render_glossary() -> None:
    for term, desc in TERMS:
        st.markdown(f"**{term}** — {desc}")
