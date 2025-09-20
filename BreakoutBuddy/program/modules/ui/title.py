from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import streamlit as st

def render():
    st.title("BreakoutBuddy — Smart Dashboard")
    st.caption("Thin app shell; pages and logic live in modules/tabs and modules/services.")
