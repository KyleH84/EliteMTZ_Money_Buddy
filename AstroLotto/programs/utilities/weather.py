# utilities/weather.py — flexible signature + friendly summary
from __future__ import annotations
from typing import Any, Dict
import math

try:
    import streamlit as st  # type: ignore
    cache_data = st.cache_data
except Exception:  # streamlit not present or in headless import
    def cache_data(*args, **kwargs):
        def deco(f): return f
        return deco

def _mph(ms: float) -> float:
    try:
        return float(ms) * 2.23693629
    except Exception:
        return 0.0

@cache_data(ttl=900)
def get_weather_by_zip(zip_code: Any, *args, units: str = "F", **kwargs) -> Dict[str, Any]:
    """Return current weather for a US ZIP. Accepts extra args for backward compatibility.
    Output:
      { ok: bool, temp_C: float|None, temp_F: float|None,
        windspeed_mps: float|None, windspeed_mph: float|None, summary: str }
    """
    # Normalize ZIP
    try:
        z = str(zip_code).strip()
        if not z or len(z) < 5:
            return {"ok": False, "summary": "invalid ZIP"}
    except Exception:
        return {"ok": False, "summary": "invalid ZIP"}

    # Geocode
    try:
        import pgeocode  # type: ignore
        nomi = pgeocode.Nominatim("us")
        rec = nomi.query_postal_code(z)
        lat, lon = float(rec.latitude), float(rec.longitude)
        if math.isnan(lat) or math.isnan(lon):
            return {"ok": False, "summary": "ZIP not found"}
    except Exception:
        return {"ok": False, "summary": "geo lookup failed"}

    # Fetch weather
    try:
        import requests  # type: ignore
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        j = r.json()
        cur = j.get("current_weather", {}) or {}
        tC = cur.get("temperature")
        ws = cur.get("windspeed")
        tF = (tC * 9/5 + 32) if tC is not None else None
        ws_mph = _mph(ws) if ws is not None else None
        if units.upper() == "F":
            t_display = f"{tF:.0f}°F" if tF is not None else "?"
        else:
            t_display = f"{tC:.0f}°C" if tC is not None else "?"
        summary = f"{t_display}, wind {ws_mph:.0f} mph" if ws_mph is not None else f"{t_display}"
        return {
            "ok": True,
            "temp_C": tC, "temp_F": tF,
            "windspeed_mps": ws, "windspeed_mph": ws_mph,
            "summary": summary,
        }
    except Exception:
        return {"ok": False, "summary": "network error"}
