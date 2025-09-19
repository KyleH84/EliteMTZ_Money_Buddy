# Program/utilities/weather_source.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import json

DRAW_SITES = {
    "powerball":        {"city":"Tallahassee","state":"FL","lat":30.4383,"lon":-84.2807},
    "megamillions":     {"city":"Atlanta","state":"GA","lat":33.7490,"lon":-84.3880},
    "colorado_lottery": {"city":"Pueblo","state":"CO","lat":38.2544,"lon":-104.6091},
    "cash5":            {"city":"Pueblo","state":"CO","lat":38.2544,"lon":-104.6091},
    "lucky_for_life":   {"city":"Rocky Hill","state":"CT","lat":41.6643,"lon":-72.6595},
    "pick3":            {"city":"Pueblo","state":"CO","lat":38.2544,"lon":-104.6091},
}

def _load_climatology(program_dir: Path, extras_dir: Path):
    for base in (extras_dir / "static", program_dir / "static"):
        f = base / "climatology.csv"
        if f.exists():
            try:
                import pandas as pd
                return pd.read_csv(f)
            except Exception:
                continue
    return None

def _nearest_station(lat: float, lon: float):
    try:
        from meteostat import Point, Stations
        stations = Stations().nearby(lat, lon).fetch(1)
        if stations is None or stations.empty: return None
        row = stations.iloc[0]
        return {"id": row["id"], "name": row.get("name")}
    except Exception:
        return None

def _daily_from_meteostat(lat: float, lon: float, d: date):
    try:
        from meteostat import Point, Daily
        import pandas as pd
        p = Point(lat, lon)
        df = Daily(p, d, d).fetch()
        if df is None or df.empty: return None
        row = df.iloc[0]
        return {
            "t_mean": float(row.get("tavg")) if row.get("tavg")==row.get("tavg") else None,
            "t_max": float(row.get("tmax")) if row.get("tmax")==row.get("tmax") else None,
            "precip": float(row.get("prcp")) if row.get("prcp")==row.get("prcp") else 0.0,
            "w_mean": float(row.get("wspd")) if row.get("wspd")==row.get("wspd") else None,
        }
    except Exception:
        return None

def daily_weather_for_site(lat: float, lon: float, d: date, program_dir: Path|None=None, extras_dir: Path|None=None):
    w = _daily_from_meteostat(lat, lon, d)
    if w: return w
    # fallback: monthly climatology
    if program_dir and extras_dir:
        clim = _load_climatology(program_dir, extras_dir)
        if clim is not None:
            import pandas as pd
            m = d.month
            nearby = clim.iloc[(clim["month"]-m).abs().argsort()[:1]]
            if not nearby.empty:
                r = nearby.iloc[0]
                return {"t_mean": float(r.get("t_mean", 65.0)),
                        "t_max": float(r.get("t_max", 75.0)),
                        "precip": float(r.get("precip", 0.0)),
                        "w_mean": float(r.get("w_mean", 7.0))}
    return {"t_mean": None, "t_max": None, "precip": 0.0, "w_mean": None}

def daily_weather_for_game(game: str, d: date):
    g=(game or "").lower()
    site = DRAW_SITES.get(g)
    if not site: return None
    from os import environ as _env
    program_dir = Path(_env.get("ASTRO_PROGRAM_DIR","Program"))
    extras_dir = Path(_env.get("ASTRO_EXTRAS_DIR","Extras"))
    return daily_weather_for_site(site["lat"], site["lon"], d, program_dir, extras_dir)
