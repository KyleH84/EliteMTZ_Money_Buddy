# AstroLotto/programs/app_main.py (patched)
# - Make load_kernel() cache with st.cache_resource (EphemerisWrapper is not pickle-serializable)
# - Auto-backfill if no cached history CSV found so the app doesn't demand manual upload
import os
import streamlit as st

from . import historical_backfill as hb

# ---- CACHE FIX ----
@st.cache_resource(show_spinner=False)
def load_kernel():
    # NOTE: keep original behavior but return the EphemerisWrapper object without serializing (resource cache)
    from utilities.ephemeris import EphemerisWrapper  # your existing helper
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
                added = hb.run_backfill_for_csv(game=game, path=path)
                results[label] = {"ok": True, "path": path, "added_rows": int(added or 0), "used": "historical_backfill.run_backfill_for_csv"}
            except Exception as e:
                results[label] = {"ok": False, "path": path, "error": f"{type(e).__name__}: {e}"}
        else:
            results[label] = {"ok": True, "path": path, "added_rows": 0, "used": "existing"}
    return results

# Call on import so pages can rely on cache presence without manual CSV upload
try:
    _ = ensure_history()
except Exception as _e:
    # Non-fatal: surfaces on UI elsewhere
    pass