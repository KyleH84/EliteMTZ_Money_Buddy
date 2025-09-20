from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# AstroLotto/programs/utilities/ephemeris.py
from pathlib import Path
from typing import Optional, Tuple, Union, Any
from skyfield.api import load, Loader

class EphemerisWrapper:
    """
    Wrap Skyfield SPK kernel so missing planet names transparently map to
    barycenters or numeric NAIF codes. This lets the rest of the code ask for
    'MARS' and still work even if the kernel only has 'MARS BARYCENTER' (4).
    """
    _name_to_codes = {
        "MERCURY": (199, 1, "1 MERCURY BARYCENTER"),
        "VENUS":   (299, 2, "2 VENUS BARYCENTER"),
        "EARTH":   (399, 3, "3 EARTH BARYCENTER"),
        "MOON":    (301,),
        "MARS":    (499, 4, "4 MARS BARYCENTER"),
        "JUPITER": (599, 5, "5 JUPITER BARYCENTER"),
        "SATURN":  (699, 6, "6 SATURN BARYCENTER"),
        "URANUS":  (799, 7, "7 URANUS BARYCENTER"),
        "NEPTUNE": (899, 8, "8 NEPTUNE BARYCENTER"),
        "SUN":     (10, "SUN"),
    }

    def __init__(self, eph):
        self._eph = eph

    def __getitem__(self, key: Union[int, str]):
        # First try original key
        try:
            return self._eph[key]
        except KeyError:
            pass

        # If string name, try remappings
        if isinstance(key, str):
            name = key.strip().upper()
            if name in self._name_to_codes:
                for alt in self._name_to_codes[name]:
                    try:
                        return self._eph[alt]
                    except KeyError:
                        continue

        # If numeric planet code is missing, try barycenter numeric
        if isinstance(key, int):
            # e.g., 499 (MARS) -> 4 (MARS BARYCENTER)
            if key in (199,299,399,499,599,699,799,899):
                try:
                    return self._eph[int(str(key)[0])]  # 499 -> 4
                except Exception:
                    pass

        # Give up
        raise KeyError(f"{key!r} not found in kernel (even after fallbacks)")

def _pkg_de440_path() -> Optional[Path]:
    """Locate de440.bsp if it’s packaged (optional)."""
    try:
        from importlib.resources import files as ir_files  # py>=3.9
        import naif_de440  # type: ignore
        cand = ir_files(naif_de440).joinpath("de440.bsp")
        p = Path(str(cand))
        return p if p.exists() else None
    except Exception:
        return None

def _has_any_planets(eph) -> bool:
    # Consider success if at least one of MERCURY/EARTH/MARS resolves
    try:
        _ = eph["MERCURY"]; _ = eph["EARTH"]; _ = eph["MARS"]
        return True
    except Exception:
        return False

def load_kernel():
    """
    Return an SPK kernel (wrapped) that supports planet access by names.
    Preference order:
      1) Local de421.bsp in AstroLotto/extras/ephemeris_cache or extras/.
      2) Packaged de440.bsp if available.
      3) Loader cache dir: try de421.bsp (download if allowed), else de440.bsp.
    """
    base = Path(__file__).resolve()

    # 1) Prefer the exact paths you have on disk
    exact_candidates = [
        base.parents[2] / "extras" / "ephemeris_cache" / "de421.bsp",
        base.parents[2] / "extras" / "de421.bsp",
    ]
    for cand in exact_candidates:
        if cand.exists():
            try:
                eph = load(str(cand))
                wrapped = EphemerisWrapper(eph)
                if _has_any_planets(wrapped):
                    print(f"[AstroLotto] Using ephemeris: {cand}")
                    return wrapped
            except Exception as e:
                print(f"[AstroLotto] Failed loading {cand}: {e}")

    # 1b) Additional common spots
    more_candidates = [
        base.parents[1] / "de421.bsp",
        base.parent / "de421.bsp",
        base.parents[2] / "programs" / "de421.bsp",
        base.parents[2] / "programs" / "utilities" / "de421.bsp",
    ]
    for cand in more_candidates:
        if cand.exists():
            try:
                eph = load(str(cand))
                wrapped = EphemerisWrapper(eph)
                if _has_any_planets(wrapped):
                    print(f"[AstroLotto] Using ephemeris: {cand}")
                    return wrapped
            except Exception as e:
                print(f"[AstroLotto] Failed loading {cand}: {e}")

    # 2) Packaged de440.bsp (optional dep)
    pkg = _pkg_de440_path()
    if pkg and pkg.exists():
        try:
            eph = load(str(pkg))
            wrapped = EphemerisWrapper(eph)
            if _has_any_planets(wrapped):
                print(f"[AstroLotto] Using packaged de440: {pkg}")
                return wrapped
        except Exception as e:
            print(f"[AstroLotto] Failed loading packaged de440: {e}")

    # 3) Loader cache directory
    cache_dir = base.parents[2] / "extras" / "ephemeris_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    loader = Loader(str(cache_dir))

    # Try de421 first
    try:
        eph = loader("de421.bsp")  # fetches if missing (if network permitted)
        wrapped = EphemerisWrapper(eph)
        if _has_any_planets(wrapped):
            print(f"[AstroLotto] Using cache ephemeris: {cache_dir / 'de421.bsp'}")
            return wrapped
    except Exception as e:
        print(f"[AstroLotto] de421 via Loader failed: {e}")

    # Fallback to de440
    try:
        eph = loader("de440.bsp")
        wrapped = EphemerisWrapper(eph)
        if _has_any_planets(wrapped):
            print(f"[AstroLotto] Using cache ephemeris: {cache_dir / 'de440.bsp'}")
            return wrapped
    except Exception as e:
        print(f"[AstroLotto] de440 via Loader failed: {e}")

    raise RuntimeError("""Could not obtain an ephemeris with individual planet targets.
I tried local files (de421.bsp), packaged 'de440.bsp', and Loader cache (de421/de440).
Place 'de421.bsp' in one of:
  ./extras/ephemeris_cache/de421.bsp
  ./extras/de421.bsp
  ./programs/de421.bsp
  ./programs/utilities/de421.bsp
Then relaunch.""")

def get_ephemeris_and_timescale() -> Tuple[object, object]:
    eph = load_kernel()
    ts = load.timescale()
    return eph, ts
