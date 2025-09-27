# BreakoutBuddy/program/modules/about.py (patched)
from __future__ import annotations

import streamlit as st

def render():
    st.subheader("About BreakoutBuddy")
    st.write("This is a lightweight About module restored to avoid a mis-placed __future__ import crash.")
    st.caption("You can edit this copy later to add your original content again.")