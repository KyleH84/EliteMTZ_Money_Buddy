# AstroLotto/programs/app_main.py (patched v2)
# - Robust imports whether executed as a package or as loose scripts
# - load_kernel cached as resource
# - Auto-backfill of game CSVs when missing/empty

import os, sys
import streamlit as st

# ---- import helpers robustly ----
def _import_ephemeris_wrapper():
    try:
        # package relative (preferred)
        from .utilities.ephemeris import EphemerisWrapper
        return EphemerisWrapper
    except Exception:
        try:
            # package absolute
            from AstroLotto.programs.utilities.ephemeris import EphemerisWrapper
            return EphemerisWrapper
        except Exception:
            # path fallback
            here = os.path.dirname(__file__)
            util_dir = os.path.join(here, "utilities")
            if util_dir not in sys.path:
                sys.path.insert(0, util_dir)
            from ephemeris import EphemerisWrapper  # type: ignore
            return EphemerisWrapper

def _import_historical_backfill():
    try:
        from . import historical_backfill as hb
        return hb
    except Exception:
        try:
            import AstroLotto.programs.historical_backfill as hb  # type: ignore
            return hb
        except Exception:
            here = os.path.dirname(__file__)
            if here not in sys.path:
                sys.path.insert(0, here)
            import historical_backfill as hb  # type: ignore
            return hb

HB = _import_historical_backfill()
EphemerisWrapper = _import_ephemeris_wrapper()

# ---- CACHE FIX ----
@st.cache_resource(show_spinner=False)
def load_kernel():
    return EphemerisWrapper()

# ---- DATA GUARANTEE ----
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "Data")

def ensure_history():
    """Ensure game CSVs exist; run backfill if missing or size==0."""
    os.makedirs(DATA_DIR, exist_ok=True)
    checks = [
        ("Mega Millions",       "cached_megamillions_data.csv", "mega_millions"),
        ("Powerball",           "cached_powerball_data.csv",    "powerball"),
        ("Colorado Cash 5",     "cached_cash5_data.csv",        "colorado_cash_5"),
        ("Lucky for Life",      "cached_luckyforlife_data.csv", "lucky_for_life"),
        ("Colorado Lotto+",     "cached_colorado_lottery_data.csv", "colorado_lotto+"),
        ("Pick 3",              "cached_pick3_data.csv",        "pick_3"),
    ]
    results = {}
    for label, fn, game in checks:
        path = os.path.join(DATA_DIR, fn)
        need = (not os.path.exists(path)) or (os.path.getsize(path) == 0)
        if need:
            try:
                added = HB.run_backfill_for_csv(game=game, path=path)
                results[label] = {"ok": True, "path": path, "added_rows": int(added or 0), "used": "historical_backfill.run_backfill_for_csv"}
            except Exception as e:
                results[label] = {"ok": False, "path": path, "error": f"{type(e).__name__}: {e}"}
        else:
            results[label] = {"ok": True, "path": path, "added_rows": 0, "used": "existing"}
    return results

try:
    _ = ensure_history()
except Exception:
    pass