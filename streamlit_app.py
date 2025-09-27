from __future__ import annotations
# --- Health widget (BreakoutBuddy-aware import) ---
try:
    from utilities.health_widget import render_health_widget  # either root-level utilities or already on sys.path
except Exception:
    import sys
    from pathlib import Path as _Path
    _bb_prog = _Path(__file__).parent / "BreakoutBuddy" / "program"
    if _bb_prog.exists() and str(_bb_prog) not in sys.path:
        sys.path.insert(0, str(_bb_prog))
    from utilities.health_widget import render_health_widget  # now import from BreakoutBuddy/program
try:
    render_health_widget()
except Exception as _hw_e:
    print("Health widget init warning:", _hw_e)
# --- end health widget ---

# --- Cloud CSV shim: route ALL pandas CSV I/O to Supabase Storage ---
# Keep this immediately after the __future__ import.
try:
    import cloud_csv_shim  # patches pandas.read_csv / DataFrame.to_csv -> Supabase
    print("Cloud CSV shim active: pandas CSV I/O mapped to Supabase 'tables' bucket")
except Exception as _shim_e:
    print("CSV shim disabled:", _shim_e)

import os, sys, runpy
from pathlib import Path
import streamlit as st

render_health_widget()

# --- Supabase status indicator (helps catch misconfigured secrets) ---
_SUPA_URL = os.getenv("SUPABASE_URL")
_SUPA_KEY = os.getenv("SUPABASE_KEY")
with st.sidebar:
    st.subheader("Storage")
    if _SUPA_URL and _SUPA_KEY:
        st.success("Supabase connected", icon="ðŸ—„ï¸")
    else:
        st.warning("Supabase not configured â€” CSV I/O will use local ephemeral filesystem.", icon="âš ï¸")


# --- Streamlit compatibility shim ---
# Older code may call st.experimental_rerun; alias it to st.rerun if missing.
try:
    import streamlit as _st_comp
    if not hasattr(_st_comp, "experimental_rerun") and hasattr(_st_comp, "rerun"):
        _st_comp.experimental_rerun = _st_comp.rerun  # type: ignore[attr-defined]
except Exception as _compat_e:
    print("Streamlit compat shim warning:", _compat_e)
# --- End shim ---

# --- Cloud paths (kept), but NO local CSV preflight anymore ---
MB_BASE_DIR = Path(os.getenv("MB_BASE_DIR", "/tmp/money_buddy"))
DATA_DIR = MB_BASE_DIR / "Data"
os.environ["BREAKOUTBUDDY_DATA"] = str(DATA_DIR)
# NOTE: we no longer create / depend on bb_snapshot.csv on local disk.
# Any pd.read_csv()/to_csv() calls anywhere in the codebase are now
# transparently handled by the Supabase-backed cloud_csv_shim.

def _run_script(path: Path, sys_paths: list[Path] = None):
    # Temporarily extend sys.path so app-local imports (e.g., 'modules') resolve
    old_sys_path = list(sys.path)
    try:
        if sys_paths:
            for p in sys_paths:
                sp = str(p)
                if sp not in sys.path:
                    sys.path.insert(0, sp)
        runpy.run_path(str(path), run_name="__main__")
    except SystemExit:
        pass  # let Streamlit rerun/stop pass
    except Exception as e:
        st.error(f"Failed to run {path}: {type(e).__name__}: {e}")
    finally:
        sys.path[:] = old_sys_path

def _discover_page_files(app_root: Path, subdirs: list[str]):
    # Return list[Path] of page scripts excluding app_main.py and __init__.py
    pages = []
    for sub in subdirs:
        p = app_root / sub
        if p.exists():
            for f in sorted(p.rglob("*.py")):
                name = f.name.lower()
                if name == "__init__.py" or name == "app_main.py":
                    continue
                pages.append(f)
    return pages

def _nice_title(p: Path):
    # Derive a tab title from filename like '2_Admin_Tools.py' -> 'Admin Tools'
    s = p.stem
    # Drop numeric/order prefixes
    while s and (s[0].isdigit() or s[0] in "_-"):
        s = s[1:]
    s = s.replace("_", " ").replace("-", " ").strip()
    return s or p.stem

st.set_page_config(page_title="EliteMTZ Money Buddy", layout="wide")

st.sidebar.title("Apps")
app_choice = st.sidebar.radio("Choose app", ["AstroLotto", "BreakoutBuddy"], index=0)

base_dir = Path(__file__).resolve().parent

if app_choice == "AstroLotto":
    app_dir = base_dir / "AstroLotto" / "programs"
    main_path = app_dir / "app_main.py"

    # Discover additional pages
    extra_pages = _discover_page_files(app_dir, ["pages", "programs/pages", "program/pages"])

    tab_titles = ["Main"] + [_nice_title(p) for p in extra_pages]
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        if main_path.exists():
            _run_script(main_path, sys_paths=[app_dir, app_dir.parent])
        else:
            st.error(f"Main file not found: {main_path}")

    for t, p in zip(tabs[1:], extra_pages):
        with t:
            _run_script(p, sys_paths=[app_dir, app_dir.parent])

else:
    # BreakoutBuddy
    app_dir = base_dir / "BreakoutBuddy"
    program_dir = app_dir / "program"
    # Detect main
    bb_main = None
    for candidate in ["app_main.py", "00_Dashboard.py", "main.py"]:
        c = program_dir / candidate
        if c.exists():
            bb_main = c
            break
    if bb_main is None:
        bb_main = program_dir / "00_Dashboard.py"

    # Discover page scripts under common locations
    extra_pages = _discover_page_files(app_dir, ["program/pages", "pages"])

    tab_titles = ["Main"] + [_nice_title(p) for p in extra_pages]
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        if bb_main.exists():
            # Ensure BB's 'modules' package resolves by adding program_dir to sys.path
            _run_script(bb_main, sys_paths=[program_dir, app_dir, base_dir])
        else:
            st.error(f"Main file not found: {bb_main}")

    for t, p in zip(tabs[1:], extra_pages):
        with t:
            _run_script(p, sys_paths=[program_dir, app_dir, base_dir])


