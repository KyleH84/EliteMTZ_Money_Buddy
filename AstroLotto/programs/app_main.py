from __future__ import annotations
from pathlib import Path
import runpy
import streamlit as st

# If other imports exist in your real file, keep them. Below we focus on DATA resolution.

def _resolve_al_data_dir() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "Data",   # AstroLotto/Data (preferred)
        here.parent / "Data",       # AstroLotto/programs/Data
        here.parents[2] / "Data",   # repo-level Data
        Path.cwd() / "Data",        # working-dir Data
    ]
    for c in candidates:
        try:
            if c.is_dir():
                return c
        except Exception:
            pass
    fb = here.parents[1] / "Data"
    fb.mkdir(parents=True, exist_ok=True)
    return fb

ROOT = Path(".")
DATA = _resolve_al_data_dir()

# NOTE: In your original file, ensure any literal "Data/runs" becomes str(DATA / "runs").
# Example:
# runs_dir=str(DATA / "runs")

# The rest of your original app_main.py should remain unchanged.
