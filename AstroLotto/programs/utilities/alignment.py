from __future__ import annotations
import math, datetime as dt
from typing import Dict, Any, Tuple, Optional, List
from pathlib import Path

# Try to import Skyfield; set HAVE_SKYFIELD accordingly.
try:
    from skyfield.api import load
    from skyfield.framelib import ecliptic_frame
    HAVE_SKYFIELD = True
except Exception:
    HAVE_SKYFIELD = False

# Local ephemeris helpers are independent of Skyfield availability.
from .ephemeris import load_kernel, get_ephemeris_and_timescale

PLANETS = [
    "mercury", "venus", "earth", "mars",
    "jupiter barycenter", "saturn barycenter", "uranus barycenter", "neptune barycenter",
]
USE_BODIES = [
    "mercury", "venus", "mars",
    "jupiter barycenter", "saturn barycenter", "uranus barycenter", "neptune barycenter",
]

def _circular_concentration(angles: List[float]) -> float:
    import numpy as np
    v = np.vstack([np.cos(angles), np.sin(angles)])
    R = float(np.linalg.norm(v.sum(axis=1))) / max(1, len(angles))
    return max(0.0, min(1.0, R))

def _conjunction_rate(angles: List[float], deg_thresh: float = 10.0) -> float:
    import numpy as np  # kept for potential future vectorization
    if len(angles) < 2:
        return 0.0
    th = math.radians(deg_thresh)
    cnt = 0
    total = 0
    for i in range(len(angles)):
        for j in range(i + 1, len(angles)):
            total += 1
            d = abs((angles[i] - angles[j] + math.pi) % (2 * math.pi) - math.pi)
            if d <= th:
                cnt += 1
    return float(cnt) / float(total) if total else 0.0

def heliocentric_longitudes(ts_dt: dt.datetime, ephem_dir: Path = Path("Data")) -> Optional[Dict[str, float]]:
    """Return heliocentric ecliptic longitudes (radians in [0, 2π)) for selected bodies at ts_dt."""
    if not HAVE_SKYFIELD:
        return None
    eph = load_kernel()
    if eph is None:
        return None
    ts = load.timescale()
    t = ts.from_datetime(ts_dt.replace(tzinfo=dt.timezone.utc))
    sun = eph["sun"]
    longs: Dict[str, float] = {}
    for name in USE_BODIES:
        body = eph[name]
        vec = sun.at(t).observe(body)
        ecl = vec.frame_latlon(ecliptic_frame)[1]
        longs[name] = float(ecl.radians % (2 * math.pi))
    return longs

def planetary_alignment_index(ts_dt: dt.datetime, ephem_dir: Path = Path("Data")) -> Dict[str, Any]:
    longs = heliocentric_longitudes(ts_dt, ephem_dir=ephem_dir)
    if not longs:
        # Smooth seasonal fallback so downstream doesn’t choke without Skyfield
        doy = ts_dt.timetuple().tm_yday
        ai = 0.5 + 0.5 * math.sin(2 * math.pi * doy / 365.25)
        return {"alignment_index": float(ai), "conjunction_rate": 0.0, "source": "fallback"}
    angles = list(longs.values())
    R = _circular_concentration(angles)
    conj = _conjunction_rate(angles, deg_thresh=10.0)
    ai = 0.7 * R + 0.3 * conj
    return {"alignment_index": float(ai), "conjunction_rate": float(conj), "source": "skyfield"}

def mercury_retrograde_flag(ts_dt: dt.datetime, ephem_dir: Path = Path("Data")) -> int:
    if not HAVE_SKYFIELD:
        return 0
    eph = load_kernel()
    if eph is None:
        return 0
    ts = load.timescale()

    def lam_at(dt0: dt.datetime) -> float:
        t = ts.from_datetime(dt0.replace(tzinfo=dt.timezone.utc))
        earth = eph["earth"]
        me = eph["mercury"]
        vec = earth.at(t).observe(me)
        lon = vec.frame_latlon(ecliptic_frame)[1].radians
        return float(lon % (2 * math.pi))

    t0 = ts_dt
    t_minus = t0 - dt.timedelta(days=1)
    t_plus = t0 + dt.timedelta(days=1)
    l1, l0, l2 = lam_at(t_minus), lam_at(t0), lam_at(t_plus)

    def unwrap(a: float, b: float) -> float:
        d = b - a
        return (d + math.pi) % (2 * math.pi) - math.pi

    d1 = unwrap(l1, l0)
    d2 = unwrap(l0, l2)
    return int(d1 > 0 and d2 < 0)
