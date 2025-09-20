from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from typing import List, Dict, Any
import streamlit as st
import pandas as pd
from utilities.predict_ui_common import _resolve_backend, _best_effort_call, _normalize_predictions

CANDIDATES = [
    ("models.lucky_for_life_model", "get_lucky_for_life_prediction"),
    ("utilities.lucky_for_life_predictor_core", "get_lucky_for_life_prediction"),
    ("utilities.prediction_core", "get_lucky_for_life_prediction"),
]

def _alignment_gamma(cosmic):
    try:
        score = float(((cosmic or {}).get("alignment") or {}).get("score", 0.5))
    except Exception:
        score = 0.5
    return 1.0 + (score - 0.5) * 0.6, score

def run_lucky_for_life_tab(config: dict):
    st.subheader("Lucky for Life")
    root_dir = config.get("root_dir")
    cosmic = config.get("cosmic")
    backend, backend_name = _resolve_backend(CANDIDATES)
    st.caption(f"Using backend: {backend_name or 'N/A'}")

    cols = st.columns([1,1,1,2])
    with cols[0]:
        num_tickets = st.number_input("How many tickets?", 1, 10, 5, 1)
    with cols[1]:
        use_hot_cold = st.toggle("Use Hot/Cold", value=True)
    with cols[2]:
        use_astro = st.toggle("Use Astro", value=False)
    with cols[3]:
        seed = st.number_input("Seed (optional)", 0, 2**31-1, 0, 1)

    pins_w = st.text_input("Pin whites (comma-separated)", value="")
    pins_s = st.text_input("Pin Lucky Ball(s) (comma-separated)", value="")

    def parse_pins(s: str) -> List[int]:
        out: List[int] = []
        for part in (s or "").replace(";",",").split(","):
            part = part.strip()
            if part.isdigit():
                out.append(int(part))
        return out

    if st.button("ðŸŽ¯ Generate Lucky for Life"):
        tickets: List[Dict[str, Any]] = []
        for _ in range(int(num_tickets)):
            if backend:
                res = _best_effort_call(backend, root_dir,
                                        k_white=5, k_special=1,
                                        use_hot_cold=use_hot_cold,
                                        use_astro=use_astro,
                                        cosmic=cosmic if use_astro else None,
                                        pinned_whites=parse_pins(pins_w) or None,
                                        pinned_specials=parse_pins(pins_s) or None,
                                        seed=int(seed) if seed else None)
            else:
                res = {"white":[1,2,3,4,5],"special":[1]}
            tickets.append(res)

        shown = _normalize_predictions(tickets if len(tickets)>1 else tickets[0])
        st.subheader("Suggested Tickets")
        for i, item in enumerate(shown, 1):
            whites = item.get("white") or []
            special = item.get("special")
            st.write(f"Ticket {i}: {sorted(whites)} + Lucky {special if special is not None else 'â€”'}")

        with st.expander("Details / Debug"):
            gamma, score = _alignment_gamma(cosmic)
            st.write(f"Alignment score: **{score:.3f}**, gamma: **{gamma:.3f}** (only applied when Use Astro is ON)")
            try:
                hist = pd.read_csv("cached_lucky_for_life_data.csv")
                wb = pd.Series(0.0, index=range(1,49))
                for c in ["n1","n2","n3","n4","n5"]:
                    if c in hist.columns:
                        wb = wb.add(hist[c].value_counts(), fill_value=0.0)
                wadj = (wb + 1e-9) ** (gamma if use_astro else 1.0)
                wboost = (wadj / (wb + 1e-9)).sort_values(ascending=False)
                st.write("Top boosted whites:", list(wboost.head(10).index))

                sb = pd.Series(0.0, index=range(1,19))
                for k in ["lb","lucky","special","n6"]:
                    if k in hist.columns:
                        sb = sb.add(hist[k].value_counts(), fill_value=0.0)
                        break
                sadj = (sb + 1e-9) ** (gamma if use_astro else 1.0)
                sboost = (sadj / (sb + 1e-9)).sort_values(ascending=False)
                st.write("Top boosted Lucky Balls:", list(sboost.head(5).index))
            except Exception as e:
                st.warning(f"No history yet for debug panel: {e}")

    if not backend:
        st.warning("No prediction backend loaded. Using a built-in fallback.")
