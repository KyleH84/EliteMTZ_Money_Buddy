from __future__ import annotations
from typing import List, Dict, Any, Optional
import streamlit as st
import pandas as pd
from utilities.predict_ui_common import _resolve_backend, _best_effort_call

CANDIDATES = [
    ("models.pick3_model", "get_pick3_prediction"),
    ("utilities.pick3_predictor_core", "get_pick3_prediction"),
    ("utilities.prediction_core", "get_pick3_prediction"),
]

def _alignment_gamma(cosmic):
    try:
        score = float(((cosmic or {}).get("alignment") or {}).get("score", 0.5))
    except Exception:
        score = 0.5
    return 1.0 + (score - 0.5) * 0.6, score

def run_pick3_tab(config: dict):
    st.subheader("Pick 3")
    root_dir = config.get("root_dir")
    cosmic = config.get("cosmic")
    backend, backend_name = _resolve_backend(CANDIDATES)
    st.caption(f"Using backend: {backend_name or 'N/A'}")

    cols = st.columns([1,1,1,2])
    with cols[0]:
        num_tickets = st.number_input("How many tickets?", 1, 20, 5, 1)
    with cols[1]:
        draw_time = st.radio("Draw time", options=["Midday","Evening"], horizontal=True)
    with cols[2]:
        use_hot_cold = st.toggle("Use Hot/Cold", value=True)
    with cols[3]:
        use_astro = st.toggle("Use Astro", value=False)

    seed = st.number_input("Seed (optional)", 0, 2**31-1, 0, 1)
    pins = st.text_input("Pin digits (e.g. 1,,7)", value="")

    def parse_pos_pins(s: str) -> List[Optional[int]]:
        parts = [p.strip() for p in (s or "").split(",")]
        out: List[Optional[int]] = []
        for p in parts[:3]:
            if p.isdigit():
                v = int(p); out.append(v if 0 <= v <= 9 else None)
            else:
                out.append(None)
        while len(out) < 3: out.append(None)
        return out

    if st.button("ðŸŽ¯ Generate Pick 3"):
        tickets: List[Dict[str, Any]] = []
        for _ in range(int(num_tickets)):
            if backend:
                res = _best_effort_call(backend, root_dir,
                                        draw_time=draw_time.lower(),
                                        use_hot_cold=use_hot_cold,
                                        use_astro=use_astro,
                                        cosmic=cosmic if use_astro else None,
                                        pinned_digits=parse_pos_pins(pins),
                                        seed=int(seed) if seed else None)
            else:
                res = {"digits":[1,2,3], "draw_time": draw_time.lower()}
            tickets.append(res)

        st.subheader("Suggested Tickets")
        for i, item in enumerate(tickets, 1):
            digits = item.get("digits") or []
            st.write(f"Ticket {i}: {digits[0]} {digits[1]} {digits[2]}  ({item.get('draw_time')})")

        with st.expander("Details / Debug"):
            gamma, score = _alignment_gamma(cosmic)
            st.write(f"Alignment score: **{score:.3f}**, gamma: **{gamma:.3f}** (only applied when Use Astro is ON)")
            try:
                fn = f"cached_pick3_{draw_time.lower()}_data.csv"
                try:
                    hist = pd.read_csv(fn)
                except Exception:
                    hist = pd.read_csv("cached_pick3_data.csv")
                cols = [c for c in hist.columns if c.lower() in ("n1","n2","n3","d1","d2","d3")]
                base = []
                for i in range(3):
                    if i < len(cols):
                        s = hist[cols[i]].value_counts().reindex(range(10), fill_value=0.0)
                    else:
                        s = pd.Series(0.0, index=range(10))
                    base.append(s.astype(float))
                adj = [(b + 1e-9) ** (gamma if use_astro else 1.0) for b in base]
                boosts = [ (a / (b + 1e-9)).sort_values(ascending=False) for a,b in zip(adj, base) ]
                st.write("Top boosted by position:",
                         {"D1": list(boosts[0].head(5).index),
                          "D2": list(boosts[1].head(5).index),
                          "D3": list(boosts[2].head(5).index)})
            except Exception as e:
                st.warning(f"No history yet for debug panel: {e}")

    if not backend:
        st.warning("No prediction backend loaded. Using a built-in fallback.")
