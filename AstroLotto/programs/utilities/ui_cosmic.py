from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/ui_cosmic.py
import streamlit as st
from datetime import date
from .cosmic_weather import get_cosmic_and_weather

def render_cosmic_weather_panel(zip_code: str|int|None, draw_date: date):
    data = get_cosmic_and_weather(zip_code, draw_date)
    cols = st.columns(4)
    cols[0].metric("Zodiac (draw date)", data.get("zodiac_sign","n/a"))
    cols[1].metric("Moon phase", f"{data.get('moon_phase_pct','n/a')}%")
    cols[2].metric("Moon quadrant", str(data.get('moon_quadrant','n/a')))
    cols[3].metric("Weather", data.get("weather","n/a"))
