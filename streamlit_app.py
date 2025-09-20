from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# streamlit_app.py — top-level launcher for AstroLotto & BreakoutBuddy

import runpy
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Elite MTZ — Apps", page_icon="🧭", layout="wide")

ROOT = Path(__file__).resolve().parent

# Map app names to their entry files
APPS = {
    # Keep AstroLotto as-is (adjust if your repo layout differs)
    "AstroLotto": ROOT / "AstroLotto" / "programs" / "app_main.py",
    # Route BreakoutBuddy to the real multi-tab main (NOT 00_Dashboard.py)
    "BreakoutBuddy": ROOT / "BreakoutBuddy" / "program" / "app_main.py",
}

st.title("Elite MTZ — App Launcher")
st.caption("Pick an app in the sidebar.")

with st.sidebar:
    app_name = st.selectbox("Choose app", list(APPS.keys()), index=1 if "BreakoutBuddy" in APPS else 0)
    st.write("Selected:", app_name)

entry = APPS.get(app_name)
if not entry:
    st.error(f"Unknown app: {app_name}")
elif not entry.exists():
    st.error(f"Entry file not found:\n{entry}")
    st.stop()

# Tiny version stamp so we can confirm cloud is running the right launcher
st.caption("Launcher build: 2025-09-19 route-to-app_main.py")

# Execute the selected app's entry file in this Streamlit session
runpy.run_path(str(entry), run_name="__main__")
