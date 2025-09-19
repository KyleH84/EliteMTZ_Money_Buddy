# Program/utilities/cosmic_weather.py
from __future__ import annotations
from datetime import datetime, date
from typing import Dict
from . import astrology
from .features_cosmic import moon_phase_frac, moon_quadrant
from .weather_source import daily_weather_for_game

def get_cosmic_and_weather(zip_code: str | int | None, draw_date: date) -> Dict:
    d = draw_date if isinstance(draw_date, date) else datetime.utcnow().date()
    sign = getattr(astrology, "get_zodiac_sign_for_date", lambda x: "Unknown")(d)
    frac = moon_phase_frac(d); phase_pct = round(frac * 100.0, 1)
    try:
        moon_q = moon_quadrant(d)
    except Exception:
        moon_q = None
    wx = daily_weather_for_game("powerball" if False else "", d)  # panel shows generic summary; predictors use per-game
    return {"zodiac_sign": sign, "moon_phase_pct": phase_pct, "moon_quadrant": moon_q, "weather": "ok" if wx else "n/a"}
