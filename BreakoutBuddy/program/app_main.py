from __future__ import annotations
from pathlib import Path
import sys
import streamlit as st

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
_PROG = _THIS.parent
if str(_PROG) not in sys.path: sys.path.insert(0, str(_PROG))

# Data/services used across tabs
from BreakoutBuddy.program.modules.data import list_universe, pull_enriched_snapshot
from BreakoutBuddy.program.modules.services.enrich import enrich_features
try:
    from BreakoutBuddy.program.modules.services.persistence_supabase import _client as _sb_client  # type: ignore
except Exception:
    _sb_client = lambda: None  # type: ignore

# Centralized sidebar controls
from BreakoutBuddy.program.modules.tabs.sidebar import render_sidebar_settings
settings = render_sidebar_settings()

# Tabs
from BreakoutBuddy.program.modules.tabs.dashboard import render_dashboard_tab
from BreakoutBuddy.program.modules.tabs.scanner import render_scanner_tab
from BreakoutBuddy.program.modules.tabs.explore import render_explore_tab
from BreakoutBuddy.program.modules.tabs.agents import render_agents_tab
from BreakoutBuddy.program.modules.tabs.single import render_single_tab
from BreakoutBuddy.program.modules.tabs.watchlist import render_watchlist_tab
from BreakoutBuddy.program.modules.tabs.admin import render_admin_tab
from BreakoutBuddy.program.modules.tabs.about import render_about_tab
from BreakoutBuddy.program.modules.tabs.elitenewsbot import render_elitenewsbot_tab

TABS = [
    ("Dashboard",    lambda: render_dashboard_tab()),
    ("Scanner",      lambda: render_scanner_tab(settings=settings, list_universe_fn=list_universe, pull_enriched_snapshot_fn=pull_enriched_snapshot, enrich_features_fn=enrich_features)),
    ("Explore",      lambda: render_explore_tab()),
    ("Agents",       lambda: render_agents_tab()),
    ("Single",       lambda: render_single_tab()),
    ("Watchlist",    lambda: render_watchlist_tab(conn=_sb_client(), settings=settings, pull_enriched_snapshot_fn=pull_enriched_snapshot, enrich_features_fn=enrich_features)),
    ("EliteNewsBot", lambda: render_elitenewsbot_tab(settings=settings)),
    ("Admin",        lambda: render_admin_tab(settings=settings)),
    ("About",        lambda: render_about_tab()),
]

tabs = st.tabs([name for name, _ in TABS])
for i, (name, fn) in enumerate(TABS):
    with tabs[i]:
        try:
            fn()
        except Exception as e:
            st.error(f"Failed to render '{name}': {type(e).__name__}: {e}")
