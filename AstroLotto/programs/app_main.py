# AstroLotto/programs/app_main.py (restored router + robust imports)
import os, sys
import streamlit as st

# ---------- Robust imports for EphemerisWrapper and backfill ----------
def _import_ephemeris_wrapper():
    try:
        from .utilities.ephemeris import EphemerisWrapper
        return EphemerisWrapper
    except Exception:
        try:
            from AstroLotto.programs.utilities.ephemeris import EphemerisWrapper  # type: ignore
            return EphemerisWrapper
        except Exception:
            here = os.path.dirname(__file__); util_dir = os.path.join(here, "utilities")
            if util_dir not in sys.path: sys.path.insert(0, util_dir)
            from ephemeris import EphemerisWrapper  # type: ignore
            return EphemerisWrapper

def _import_backfill():
    try:
        from . import historical_backfill as hb
        return hb
    except Exception:
        try:
            import AstroLotto.programs.historical_backfill as hb  # type: ignore
            return hb
        except Exception:
            here = os.path.dirname(__file__)
            if here not in sys.path: sys.path.insert(0, here)
            import historical_backfill as hb  # type: ignore
            return hb

HB = _import_backfill()
EphemerisWrapper = _import_ephemeris_wrapper()

# ---------- Kernel caching ----------
@st.cache_resource(show_spinner=False)
def load_kernel():
    return EphemerisWrapper()

# ---------- Data bootstrap (CSV cache) ----------
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "Data")

def ensure_history():
    os.makedirs(DATA_DIR, exist_ok=True)
    checks = [
        ("Mega Millions",       "cached_megamillions_data.csv",      "mega_millions"),
        ("Powerball",           "cached_powerball_data.csv",         "powerball"),
        ("Colorado Cash 5",     "cached_cash5_data.csv",             "colorado_cash_5"),
        ("Lucky for Life",      "cached_luckyforlife_data.csv",      "lucky_for_life"),
        ("Colorado Lotto+",     "cached_colorado_lottery_data.csv",  "colorado_lotto+"),
        ("Pick 3",              "cached_pick3_data.csv",             "pick_3"),
    ]
    for _, fn, game in checks:
        path = os.path.join(DATA_DIR, fn)
        need = (not os.path.exists(path)) or (os.path.getsize(path) == 0)
        if need:
            try:
                HB.run_backfill_for_csv(game=game, path=path)
            except Exception as e:
                # Non-fatal: we surface errors in the UI panels that need them
                print(f"[AstroLotto] Backfill failed for {game}: {type(e).__name__}: {e}")

try:
    ensure_history()
except Exception as _e:
    print("[AstroLotto] ensure_history error:", _e)

# ---------- Page registry ----------
def _import_page(modname):
    # Try relative, then absolute, then path
    try:
        module = __import__(f".pages.{modname}", fromlist=["*"])
        return module
    except Exception:
        try:
            module = __import__(f"AstroLotto.programs.pages.{modname}", fromlist=["*"])  # type: ignore
            return module
        except Exception as e:
            # Fallback stub so app doesn't go blank
            class _Stub:
                def render(self):
                    st.error(f"AstroLotto page '{modname}' failed to import: {type(e).__name__}: {e}")
            return _Stub()

def get_tabs():
    """Return dict of tab_name -> callable render()."""
    pages = {
        "main":     getattr(_import_page("main"), "render", lambda: st.write("Main page missing")),
        "about":    getattr(_import_page("about"), "render", lambda: st.write("About missing")),
        "admin":    getattr(_import_page("admin"), "render", lambda: st.write("Admin missing")),
        "agent":    getattr(_import_page("agent"), "render", lambda: st.write("Agent missing")),
        "autotune": getattr(_import_page("autotune"), "render", lambda: st.write("Autotune missing")),
        "glossary": getattr(_import_page("glossary"), "render", lambda: st.write("Glossary missing")),
    }
    return pages

# Optional convenience so some routers call app_main.render()
def render(tab_name: str = "main"):
    tabs = get_tabs()
    fn = tabs.get(tab_name, tabs["main"])
    return fn()