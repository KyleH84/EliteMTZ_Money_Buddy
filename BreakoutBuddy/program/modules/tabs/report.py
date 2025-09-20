from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import streamlit as st
import pandas as pd
from pathlib import Path
from modules import explain as explain_mod

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

def render_report_tab(**kwargs):
    st.header("Report")
    p = _data_dir() / "ranked_latest.csv"
    if not p.exists():
        st.info("No ranked CSV yet. Run a rank once.")
        return
    try:
        df = pd.read_csv(p)
    except Exception as e:
        st.error(f"Failed to read ranked CSV: {e}")
        return
    try:
        table = explain_mod.explain_scan(df)
        st.dataframe(table, height=520, width='stretch')
        if st.button("Download report CSV"):
            out = _data_dir() / "report_latest.csv"
            table.to_csv(out, index=False)
            st.success(f"Saved {out}")
    except Exception as e:
        st.error(f"Report build failed: {e}")
