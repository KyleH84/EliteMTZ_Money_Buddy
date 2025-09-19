from __future__ import annotations
from typing import Any, Optional, List, Dict, Tuple
import streamlit as st
import pandas as pd
from utilities.predict_ui_common import _resolve_backend, _best_effort_call

CANDIDATES: List[Tuple[str,str]] = [
    ("utilities.colorado_lottery_predictor_core", "get_colorado_lottery_prediction"),
    ("models.colorado_lottery_model", "get_colorado_lottery_prediction"),
    ("utilities.prediction_core", "get_colorado_lottery_prediction"),
]

def _alignment_gamma(cosmic: Optional[Dict[str, Any]]) -> float:
    try:
        score = float(((cosmic or {}).get("alignment") or {}).get("score", 0.5))
    except Exception:
        score = 0.5
    return 1.0 + (score - 0.5) * 0.6, score

def run_colorado_lottery_tab(config: dict):
    root_dir = config.get("root_dir")
    cosmic = config.get("cosmic")
    st.subheader("Colorado Lotto+")
    backend, backend_name = _resolve_backend(CANDIDATES)
    st.caption(f"Using backend: {backend_name or 'N/A'}")

    cols = st.columns([1,1,1,1])
    with cols[0]:
        num_tickets = st.number_input("How many tickets?", 1, 10, 5, 1)
    with cols[1]:
        use_hot_cold = st.toggle("Use Hot/Cold", value=True)
    with cols[2]:
        use_astro = st.toggle("Use Astro", value=False)
    with cols[3]:
        seed = st.number_input("Seed (optional)", 0, 2**31-1, 0, 1)

    if st.button("ðŸŽ¯ Generate Colorado Lotto+ Predictions"):
        tickets: List[List[int]] = []
        for _ in range(int(num_tickets)):
            if backend:
                try:
                    res = _best_effort_call(backend, root_dir, k_white=6,
                                            use_hot_cold=use_hot_cold,
                                            use_astro=use_astro,
                                            cosmic=cosmic if use_astro else None,
                                            seed=int(seed) if seed else None)
                except TypeError:
                    res = _best_effort_call(backend, root_dir, k_white=6)
            else:
                import random
                res = {"white": sorted(random.sample(list(range(1,41)), 6))}
            whites = res.get("white") or res.get("numbers") or []
            whites = sorted(list(map(int, whites)))[:6]
            tickets.append(whites)

        st.subheader("Suggested Tickets")
        for i, nums in enumerate(tickets, 1):
            st.write(f"Ticket {i}: {nums}")

        with st.expander("Details / Debug"):
            gamma, score = _alignment_gamma(cosmic)
            st.write(f"Alignment score: **{score:.3f}**, gamma: **{gamma:.3f}** (only applied when Use Astro is ON)")
            try:
                hist = pd.read_csv("cached_colorado_lottery_data.csv")
                maxv = int(pd.to_numeric(hist[["n1","n2","n3","n4","n5","n6"]], errors="coerce").max().max())
                base = pd.Series(0.0, index=range(1, max(41, maxv+1)))
                for c in ["n1","n2","n3","n4","n5","n6"]:
                    if c in hist.columns:
                        base = base.add(hist[c].value_counts(), fill_value=0.0)
                adj = (base + 1e-9) ** (gamma if use_astro else 1.0)
                boost = (adj / (base + 1e-9)).sort_values(ascending=False)
                st.write("Top boosted numbers:", list(boost.head(10).index))
            except Exception as e:
                st.warning(f"No history yet for debug panel: {e}")

    st.caption("Official draw history appears below on the main page. Hot/Cold charts use official draws.")
