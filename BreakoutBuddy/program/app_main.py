from __future__ import annotations

# ### PATH BOOTSTRAP
import os, sys
_THIS_DIR = os.path.dirname(__file__)
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
for _p in (_REPO_ROOT, _SRC_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import importlib
import pkgutil
import streamlit as st

st.set_page_config(page_title="BreakoutBuddy", layout="wide")

st.title("BreakoutBuddy")
st.caption("BB build: safe import; robust fallback")

# ---- Discover pages dynamically from BreakoutBuddy.program.pages, excluding reporting_fixed ----
from . import pages as _pages_pkg  # type: ignore

def _list_pages():
    mods = []
    for m in pkgutil.iter_modules(_pages_pkg.__path__):
        name = m.name
        if name.lower() in {"reporting_fixed", "reporting_fixed_page", "reporting"}:
            continue  # exclude; rendered under Admin -> Utilities
        mods.append(name)
    # Prefer order: main-like first, watchlist near top, rest alphabetical
    def _key(n: str):
        if "main" in n.lower(): return (0, n)
        if "watchlist" in n.lower(): return (1, n)
        return (2, n)
    return sorted(mods, key=_key)

_page_names = _list_pages()
tabs = st.tabs(["Main"] + [n.replace("_", " ") for n in _page_names] + ["admin"])

# Main tab may be simple overview
with tabs[0]:
    st.write("Welcome to BreakoutBuddy. Select a tab or open Admin for Utilities.")

# Render discovered pages
for idx, mod_name in enumerate(_page_names, start=1):
    with tabs[idx]:
        try:
            mod = importlib.import_module(f".pages.{mod_name}", package=__package__)
            # Call a conventional renderer if present
            if hasattr(mod, "render_page"):
                mod.render_page()  # type: ignore
            elif hasattr(mod, "render_watchlist_page"):
                mod.render_watchlist_page()  # type: ignore
            else:
                st.info(f"Page '{mod_name}' has no render_* function.")
        except Exception as e:
            st.error(f"Failed to render page '{mod_name}': {e}")

# Admin -> Utilities (Reporting Fixed)
try:
    from .modules.tabs.admin import render_admin  # type: ignore
    with tabs[len(_page_names) + 1]:
        render_admin()
except Exception as e:
    with tabs[len(_page_names) + 1]:
        st.error(f"Admin panel failed to load: {e}")