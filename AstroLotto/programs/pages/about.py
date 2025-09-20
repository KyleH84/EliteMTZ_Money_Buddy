from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import streamlit as st

st.set_page_config(page_title="About AstroLotto", layout="wide")
APP_VERSION = "v17"
st.title(f"About AstroLotto {APP_VERSION}")
st.info("See the **Glossary** page for definitions: κ, Δt, dt_K, entropy, oracle, quantum options, etc.")

with st.expander("What is AstroLotto?", expanded=True):
    st.markdown(
        """
        AstroLotto blends **history**, **per‑ball ML**, **hot/cold stats**, and **Oracle signals**
        (moon phase, geomagnetic Kp, solar flares, market proxy, and planetary alignments)
        to produce one high‑confidence pick plus optional diverse alternates.
        """
    )

with st.expander("Where things live"):
    st.code(
        "Data/                      # CSVs, caches, artifacts\n"
        "programs/app_main.py       # Main app (predictions UI)\n"
        "programs/pages/admin.py    # Admin: Data & Health, Analytics, Models, Tools\n"
        "programs/pages/about.py    # This page",
        language="text",
    )

with st.expander("Tips"):
    st.markdown(
        "- If x3 sets look too similar: increase **Min diff**, **Min unique specials**, raise **Exploration temp**, widen **Shortlist K**.\n"
        "- If predictions feel too random: lower **Decoherence**, **Exploration temp**, and **Hot/Cold influence**.\n"
        "- If hot/cold shows nothing: run **Backfill now** then **Refresh ALL caches**.\n"
        "- For jackpot display issues: confirm internet and review `programs/utilities/jackpots.py` providers."
    )
