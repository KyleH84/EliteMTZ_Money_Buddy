from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# utilities/astrology.py — add-only: includes get_user_sign_from_birthday
from datetime import date as dt_date, datetime, timedelta
import math
from typing import Union, Dict, Any

try:
    import ephem  # type: ignore
except Exception:
    ephem = None

# ---------- Zodiac helpers ----------
_ZODIAC = [
    ("Capricorn", (12, 22), (1, 19)),
    ("Aquarius",  (1, 20),  (2, 18)),
    ("Pisces",    (2, 19),  (3, 20)),
    ("Aries",     (3, 21),  (4, 19)),
    ("Taurus",    (4, 20),  (5, 20)),
    ("Gemini",    (5, 21),  (6, 20)),
    ("Cancer",    (6, 21),  (7, 22)),
    ("Leo",       (7, 23),  (8, 22)),
    ("Virgo",     (8, 23),  (9, 22)),
    ("Libra",     (9, 23),  (10, 22)),
    ("Scorpio",   (10, 23), (11, 21)),
    ("Sagittarius",(11, 22),(12, 21)),
]

def _parse_birthday(b: Union[str, dt_date, datetime]) -> dt_date:
    if isinstance(b, dt_date) and not isinstance(b, datetime):
        return b
    if isinstance(b, datetime):
        return b.date()
    s = str(b).strip().replace("/", "-")
    for fmt in ("%Y-%m-%d", "%Y-%m", "%m-%d-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    # try loose split
    parts = s.split("-")
    if len(parts) >= 3:
        try:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            return dt_date(y, m, d)
        except Exception:
            pass
    raise ValueError(f"Unrecognized birthday format: {b!r}")

def get_zodiac_sign(d: Union[str, dt_date, datetime]) -> str:
    dt = _parse_birthday(d)
    m, day = dt.month, dt.day
    for name, start, end in _ZODIAC:
        sm, sd = start; em, ed = end
        if sm <= em:
            if (m > sm or (m == sm and day >= sd)) and (m < em or (m == em and day <= ed)):
                return name
        else:  # wraps year-end (Capricorn)
            if (m > sm or (m == sm and day >= sd)) or (m < em or (m == em and day <= ed)):
                return name
    return "Capricorn"

# Back-compat export expected by pages
def get_user_sign_from_birthday(birthday: Union[str, dt_date, datetime]) -> str:
    """Return Western zodiac sign for a given birthday.
    Accepts 'YYYY-MM-DD' or 'YYYY/MM/DD', datetime.date, or datetime.
    """
    try:
        return get_zodiac_sign(birthday)
    except Exception:
        return "Capricorn"

# ---------- Existing cosmic helpers (with summaries) ----------
def _clamp01(x: float) -> float:
    try: return max(0.0, min(1.0, float(x)))
    except Exception: return 0.0

def get_moon_phase(date=None):
    date = date or dt_date.today()
    if ephem is None:
        base = dt_date(2000, 1, 6)
        days = (date - base).days % 30
        return round((days / 29.53), 3)
    try:
        m = ephem.Moon(); m.compute(date)
        return float((m.phase or 0.0) / 100.0)
    except Exception:
        return 0.0

def get_moon_position(date=None):
    date = date or dt_date.today()
    if ephem is None:
        return {"ra": 0.0, "dec": 0.0, "summary": "RA 0.00h, Dec 0.00°"}
    try:
        m = ephem.Moon(); m.compute(date)
        ra = float(getattr(m, "ra", 0.0))
        dec = float(getattr(m, "dec", 0.0))
        ra_hours = ra * 12.0 / math.pi
        dec_deg = dec * 180.0 / math.pi
        return {"ra": ra, "dec": dec, "summary": f"RA {ra_hours:.2f}h, Dec {dec_deg:.2f}°"}
    except Exception:
        return {"ra": 0.0, "dec": 0.0, "summary": "RA 0.00h, Dec 0.00°"}

def get_mercury_retrograde(date=None):
    date = date or dt_date.today()
    if ephem is None:
        return False
    try:
        mercury = ephem.Mercury(); mercury.compute(date)
        mercury_next = ephem.Mercury(); mercury_next.compute(date + timedelta(days=1))
        return float(mercury.ra) > float(mercury_next.ra)
    except Exception:
        return False

def _ecliptic_longitude(obj) -> float:
    if ephem is None:
        return 0.0
    ecl = ephem.Ecliptic(obj)
    try: lon_rad = float(ecl.lon)
    except Exception: lon_rad = 0.0
    deg = (lon_rad * 180.0 / math.pi) % 360.0
    if deg < 0: deg += 360.0
    return deg

def _circ_resultant_length(degrees_list):
    if not degrees_list: return 0.0
    sx = 0.0; sy = 0.0
    for d in degrees_list:
        a = float(d) * math.pi / 180.0
        sx += math.cos(a); sy += math.sin(a)
    n = max(1.0, float(len(degrees_list)))
    return _clamp01((sx*sx + sy*sy) ** 0.5 / n)

def get_planetary_alignment_score(date=None, bodies=None, **kwargs) -> Dict[str, Any]:
    date = date or dt_date.today()
    bodies = bodies or ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn"]
    if ephem is None:
        phase = get_moon_phase(date)
        d = min(abs(phase - 0.0), abs(phase - 0.5), abs(phase - 1.0))
        score = 1.0 - min(1.0, d * 2.0)
        return {"score": _clamp01(score), "details": {"ephem": False, "phase": phase, "summary": f"Phase {phase*100:.0f}%"}}

    longs = []
    details: Dict[str, Any] = {"ephem": True, "longitudes": {}}
    names_out = []
    try:
        obj_map = {
            "Sun": ephem.Sun, "Moon": ephem.Moon, "Mercury": ephem.Mercury,
            "Venus": ephem.Venus, "Mars": ephem.Mars, "Jupiter": ephem.Jupiter,
            "Saturn": ephem.Saturn, "Uranus": getattr(ephem, "Uranus", None),
            "Neptune": getattr(ephem, "Neptune", None), "Pluto": getattr(ephem, "Pluto", None),
        }
        for name in bodies:
            cls = obj_map.get(name)
            if cls is None: continue
            obj = cls(); obj.compute(date)
            lon = _ecliptic_longitude(obj)
            longs.append(lon)
            details["longitudes"][name] = lon
            names_out.append(f"{name} {lon:.1f}°")
    except Exception as e:
        phase = get_moon_phase(date)
        d = min(abs(phase - 0.0), abs(phase - 0.5), abs(phase - 1.0))
        score = 1.0 - min(1.0, d * 2.0)
        return {"score": _clamp01(score), "details": {"ephem": bool(ephem), "phase": phase, "error": str(e), "summary": f"Phase {phase*100:.0f}%"}}

    score = _circ_resultant_length(longs)
    details["summary"] = f"Aligned {score:.2f} — " + ", ".join(names_out[:7])
    return {"score": _clamp01(score), "details": details}
