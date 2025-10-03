from __future__ import annotations
from pathlib import Path
import sys
import streamlit as st

_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_PROG_DIR = _THIS.parent
if str(_PROG_DIR) not in sys.path:
    sys.path.insert(0, str(_PROG_DIR))

# ---- Bring in data/services so we can pass required kwargs to tabs ----
from BreakoutBuddy.program.modules.data import list_universe, pull_enriched_snapshot
from BreakoutBuddy.program.modules.services.enrich import enrich_features
try:
    # Optional Supabase client for watchlist tab
    from BreakoutBuddy.program.modules.services.persistence_supabase import _client as _sb_client  # type: ignore
except Exception:
    _sb_client = lambda: None  # type: ignore

# ---- Global sidebar controls (persist via session_state) ----
if "universe_size" not in st.session_state:
    st.session_state["universe_size"] = 500
if "rows_to_display" not in st.session_state:
    st.session_state["rows_to_display"] = 25
st.sidebar.number_input("Universe size", min_value=50, max_value=5000, step=50, key="universe_size")
st.sidebar.number_input("Rows to display", min_value=5, max_value=200, step=5, key="rows_to_display")

# ---- Import tab renderers ----
from BreakoutBuddy.program.modules.tabs.dashboard import render_dashboard_tab
from BreakoutBuddy.program.modules.tabs.scanner import render_scanner_tab
from BreakoutBuddy.program.modules.tabs.explore import render_explore_tab
from BreakoutBuddy.program.modules.tabs.agents import render_agents_tab
from BreakoutBuddy.program.modules.tabs.single import render_single_tab
from BreakoutBuddy.program.modules.tabs.watchlist import render_watchlist_tab
from BreakoutBuddy.program.modules.tabs.admin import render_admin_tab
from BreakoutBuddy.program.modules.tabs.about import render_about_tab

TABS = [
    ("Dashboard", lambda: render_dashboard_tab()),
    ("Scanner",   lambda: render_scanner_tab(settings=st.session_state, list_universe_fn=list_universe, pull_enriched_snapshot_fn=pull_enriched_snapshot, enrich_features_fn=enrich_features)),
    ("Explore",   lambda: render_explore_tab()),
    ("Agents",    lambda: render_agents_tab()),
    ("Single",    lambda: render_single_tab()),
    ("Watchlist", lambda: render_watchlist_tab(conn=_sb_client(), settings=st.session_state, pull_enriched_snapshot_fn=pull_enriched_snapshot, enrich_features_fn=enrich_features)),
    ("Admin",     lambda: render_admin_tab(settings=st.session_state)),
    ("About",     lambda: render_about_tab()),
]

tabs = st.tabs([name for name, _ in TABS])
for i, (name, fn) in enumerate(TABS):
    with tabs[i]:
        try:
            fn()
        except Exception as e:
            st.error(f"Failed to render '{name}': {type(e).__name__}: {e}")
