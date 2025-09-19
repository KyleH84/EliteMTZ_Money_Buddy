# programs/utilities/planetary_alignment.py
from __future__ import annotations
import math
import shutil
import datetime as dt
from typing import Dict, Any, Optional

def _try_copy_de440_from_pip(dest: Path) -> Optional[Path]:
    """
    If the PyPI package `naif-de440` is installed, copy its bundled kernel into `dest`.
    Returns the path to the copied file, or None if not available.
    """
    try:
        # Common export style: module variable with absolute path
        try:
            from naif_de440 import de440  # type: ignore
            src = Path(str(de440))
            if src.exists():
                shutil.copyfile(src, dest)
                return dest
        except Exception:
            pass

        # Fallback: use importlib.resources (Python 3.9+)
        try:
            import importlib.resources as ir
            try:
                pkg_files = ir.files("naif_de440")  # type: ignore[attr-defined]
                cand = pkg_files.joinpath("de440.bsp")
                if cand.exists():
                    shutil.copyfile(str(cand), str(dest))
                    return dest
            except Exception:
                # Older Python might not support .files; try path extraction
                with ir.path("naif_de440", "de440.bsp") as p:  # type: ignore[arg-type]
                    if Path(p).exists():
                        shutil.copyfile(str(p), str(dest))
                        return dest
        except Exception:
            pass
    except Exception:
        pass
    return None

def _load_ephemeris():
    """
    Prefer DE440 (local or from `naif-de440`), then DE421.
    Returns (eph, tag) where tag is 'de440' or 'de421'.
    """
    try:
        from skyfield.api import load
    except Exception:
        return None, None

    # 1) Prefer local de440.bsp in working dir
    for fname, tag in (("de440.bsp", "de440"),):
        try:
            eph = load(fname)
            return eph, tag
        except Exception:
            pass

    # 2) If not present, try to copy from the pip package into CWD, then load
    copied = _try_copy_de440_from_pip(Path("de440.bsp"))
    if copied is not None and copied.exists():
        try:
            eph = load(str(copied))
            return eph, "de440"
        except Exception:
            pass

    # 3) Fall back to DE421 locally or via Skyfield's cache
    for fname, tag in (("de421.bsp", "de421"),):
        try:
            eph = load(fname)
            return eph, tag
        except Exception:
            pass

    return None, None

def _angular_sep_rad(a: float, b: float) -> float:
    d = abs(a - b) % (2.0 * math.pi)
    if d > math.pi:
        d = 2.0 * math.pi - d
    return d

def planetary_features_for_date(date: dt.date) -> Dict[str, Any]:
    """
    Compute a Planetary Alignment Index (PAI) and related features using Skyfield if available.
    Falls back to neutral values if ephemerides are missing or internet is blocked.

    Returns keys:
      alignment_index [0..1], conjunction_rate (pairs within 10°),
      mercury_retro (bool), pair_separations_mean (deg),
      meta: {ephemeris: 'de440'|'de421'|None, fallback: bool, copied_from_pip: bool}
    """
    try:
        from skyfield.api import load
    except Exception:
        return {
            "alignment_index": 0.0,
            "conjunction_rate": 0,
            "mercury_retro": False,
            "pair_separations_mean": 90.0,
            "meta": {"ephemeris": None, "fallback": True, "copied_from_pip": False},
        }

    eph, used = _load_ephemeris()
    if eph is None:
        return {
            "alignment_index": 0.0,
            "conjunction_rate": 0,
            "mercury_retro": False,
            "pair_separations_mean": 90.0,
            "meta": {"ephemeris": None, "fallback": True, "copied_from_pip": False},
        }

    # Track whether we copied from pip
    copied_from_pip = Path("de440.bsp").exists()

    ts = load.timescale()
    t = ts.utc(date.year, date.month, date.day, 12, 0, 0)

    bodies = ["sun", "moon", "mercury", "venus", "mars", "jupiter barycenter", "saturn barycenter"]

    longitudes = {}
    try:
        for name in bodies:
            astro = eph["earth"].at(t).observe(eph[name]).apparent().ecliptic_latlon()
            longitudes[name] = float(astro[1].radians)
    except Exception:
        return {
            "alignment_index": 0.0,
            "conjunction_rate": 0,
            "mercury_retro": False,
            "pair_separations_mean": 90.0,
            "meta": {"ephemeris": used, "fallback": True, "copied_from_pip": copied_from_pip},
        }

    # Pairwise separations
    names = list(longitudes)
    seps_deg = []
    conj = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            d = _angular_sep_rad(longitudes[names[i]], longitudes[names[j]])
            deg = math.degrees(d)
            seps_deg.append(deg)
            if deg <= 10.0:
                conj += 1

    mean_sep = sum(seps_deg) / len(seps_deg) if seps_deg else 90.0
    align_idx = max(0.0, min(1.0, 1.0 - (mean_sep / 180.0)))

    # Mercury retrograde (crude): check if longitude decreases day-to-day
    longs_mer = []
    for dd in (-1, 0, 1):
        tt = ts.utc(date.year, date.month, date.day + dd, 12, 0, 0)
        astro = eph["earth"].at(tt).observe(eph["mercury"]).apparent().ecliptic_latlon()
        longs_mer.append(float(astro[1].degrees))
    mercury_retro = longs_mer[-1] < longs_mer[-2]

    return {
        "alignment_index": float(align_idx),
        "conjunction_rate": int(conj),
        "mercury_retro": bool(mercury_retro),
        "pair_separations_mean": float(mean_sep),
        "meta": {"ephemeris": used, "fallback": False, "copied_from_pip": copied_from_pip},
    }
