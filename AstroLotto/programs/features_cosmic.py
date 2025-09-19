# Program/utilities/features_cosmic.py
from __future__ import annotations
from datetime import datetime, date, timezone
from pathlib import Path
import json, math
import pandas as pd

def zodiac_ordinal(d: date) -> int:
    m, day = d.month, d.day
    signs=[((1,20),"Aquarius"),((2,19),"Pisces"),((3,21),"Aries"),((4,20),"Taurus"),
           ((5,21),"Gemini"),((6,21),"Cancer"),((7,23),"Leo"),((8,23),"Virgo"),
           ((9,23),"Libra"),((10,23),"Scorpio"),((11,22),"Sagittarius"),((12,22),"Capricorn")]
    idx=11
    for i,(start,_name) in enumerate(signs):
        sm,sd = start
        if (m,day) < (sm,sd):
            idx = (i-1) % 12; break
    return idx

_EPOCH = datetime(2000,1,6,18,14, tzinfo=timezone.utc)  # near new moon
_SYNODIC = 29.530588853  # d
def moon_phase_frac(d: date) -> float:
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    days = (dt - _EPOCH).total_seconds() / 86400.0
    frac = (days % _SYNODIC) / _SYNODIC
    return float(frac)

def moon_quadrant(d: date) -> int:
    return int((moon_phase_frac(d) * 4.0) % 4)

def mercury_retrograde_flag(d: date, extras_dir: Path, program_dir: Path) -> int:
    # read from Extras/static/retrograde.json or Program/static/retrograde.json
    for base in (extras_dir / "static", program_dir / "static"):
        f = base / "retrograde.json"
        if f.exists():
            try:
                arr = json.loads(f.read_text(encoding="utf-8"))
                for it in arr:
                    s = pd.to_datetime(it.get("start")).date()
                    e = pd.to_datetime(it.get("end")).date()
                    if s <= d <= e: return 1
            except Exception:
                continue
    return 0
