from __future__ import annotations
# BreakoutBuddy/program/app_main.py — fixed tabs + robust imports

from pathlib import Path
import sys
import streamlit as st

# --- PATH BOOTSTRAP: put repo root on sys.path so absolute imports work ---
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[2]  # .../EliteMTZ_Money_Buddy
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# --- Import tab renderers from modules/tabs (Reporting lives under Admin) ---
from BreakoutBuddy.program.modules.tabs.dashboard import render_dashboard_tab
from BreakoutBuddy.program.modules.tabs.scanner import render_scanner_tab
from BreakoutBuddy.program.modules.tabs.explore import render_explore_tab
from BreakoutBuddy.program.modules.tabs.agents import render_agents_tab
from BreakoutBuddy.program.modules.tabs.single import render_single_tab
from BreakoutBuddy.program.modules.tabs.watchlist import render_watchlist_tab
from BreakoutBuddy.program.modules.tabs.about import render_about_tab
from BreakoutBuddy.program.modules.tabs.admin import render_admin_tab  # includes Reporting Fixed panel

st.set_page_config(page_title="BreakoutBuddy", layout="wide")

TABS: list[tuple[str, callable]] = [
    ("Dashboard", render_dashboard_tab),
    ("Scanner",   render_scanner_tab),
    ("Explore",   render_explore_tab),
    ("Agents",    render_agents_tab),
    ("Single",    render_single_tab),
    ("Watchlist", render_watchlist_tab),
    ("Admin",     render_admin_tab),      # Reporting Fixed is under Admin → Utilities
    ("About",     render_about_tab),
]

tabs = st.tabs([name for name, _ in TABS])
for i, (name, fn) in enumerate(TABS):
    with tabs[i]:
        try:
            fn()
        except Exception as e:
            st.error(f"Failed to render '{name}': {type(e).__name__}: {e}")
