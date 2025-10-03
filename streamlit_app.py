from __future__ import annotations
import streamlit as st
from pathlib import Path
import runpy, sys

st.set_page_config(page_title="EliteMTZ Money Buddy", layout="wide")

base_dir = Path(__file__).resolve().parent
apps = ["AstroLotto", "BreakoutBuddy"]
app_choice = st.sidebar.selectbox("Choose App", apps, index=1)

def _run_script(path: Path, sys_paths: list[Path]):
    # Add both app directory and repo root
    for p in sys_paths:
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)
    runpy.run_path(str(path), run_name="__main__")

if app_choice == "AstroLotto":
    app_dir = base_dir / "AstroLotto"
    program_dir = app_dir / "programs"
    al_main = program_dir / "app_main.py"
    if al_main.exists():
        _run_script(al_main, sys_paths=[program_dir, app_dir, base_dir])
    else:
        st.error(f"Main file not found: {al_main}")
else:
    # BreakoutBuddy: flattened to single entrypoint app_main.py
    app_dir = base_dir / "BreakoutBuddy"
    program_dir = app_dir / "program"
    bb_main = program_dir / "app_main.py"
    if bb_main.exists():
        _run_script(bb_main, sys_paths=[program_dir, app_dir, base_dir])
    else:
        st.error(f"Main file not found: {bb_main}")
