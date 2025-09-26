# program/app_main.py
from __future__ import annotations

import os
from pathlib import Path
import streamlit as st
from modules.tabs.about import render_about_tab
from modules.tabs.elitenewsbot import render_elitenewsbot_tab

# Try to import duckdb, but don't crash if unavailable (e.g., Python 3.13 on Windows)
DUCK_OK = True
conn = None
try:
    import duckdb  # type: ignore
except Exception as e:
    DUCK_OK = False
    duck_error = str(e)

APP_ROOT = Path(__file__).resolve().parents[1]  # program/
BB_ROOT = APP_ROOT.parents[0]                   # BreakoutBuddy root
DATA_DIR = BB_ROOT / "Data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Connect if duckdb works
if DUCK_OK:
    try:
        db_path = DATA_DIR / "bb.duckdb"
        conn = duckdb.connect(str(db_path))
    except Exception as e:
        DUCK_OK = False
        duck_error = str(e)

# Top-nav
st.set_page_config(page_title="BreakoutBuddy", layout="wide")
st.title("BreakoutBuddy")
st.caption("BB build: 2025-09-19 (safe duckdb import; robust quick explain fallback)")

# If duckdb failed, warn but keep going
if not DUCK_OK:
    st.warning("DuckDB not available. Continuing without DB features.\n\n"
               "Tip: Use Python 3.11/3.12 or install a compatible DuckDB wheel. "
               f"Details: {duck_error}")

# Sidebar controls (example/common keys so tabs can read them)
with st.sidebar:
    st.header("Controls")
    st.session_state.setdefault("controls_top_n", st.slider("Top N", 10, 100, 25, 5))
    st.session_state.setdefault("universe_size", st.slider("Universe size", 50, 1000, 300, 50))
    st.selectbox("Sort by", ["Combined", "Combined_with_agents", "ChangePct"], index=0, key="sort_by")
    st.toggle("Plain-English Why", value=True, key="plain_english_on")

# Tabs
from modules.tabs.dashboard import render_dashboard_tab
from modules.tabs.single import render_single_tab
from modules.tabs.explore import render_explore_tab
from modules.ui.watchlist_page import render as render_watchlist_page
from modules.tabs.admin import render_admin_tab
try:
    from modules.tabs.agents import render_agents_tab
except Exception:
    def render_agents_tab(**kwargs):
        st.subheader("Agents")
        st.info("Agents tab unavailable in this environment.")

tab = st.tabs(["Dashboard", "Single", "Explore", "Watchlist", "Report", "Agents", "Admin", "About", "EliteNewsBot"])

with tab[0]:
    render_dashboard_tab(settings=st.session_state, has_agents=True)

with tab[1]:
    render_single_tab(settings=st.session_state)

with tab[2]:
    try:
        render_explore_tab(settings=st.session_state, conn=conn, enrich_features_fn=None)
    except Exception as e:
        st.error(f"Explore failed: {e}")

with tab[3]:
    try:
        render_watchlist_page(conn=conn, settings=st.session_state, enrich_features_fn=None, header=True)
    except Exception as e:
        st.error(f"Watchlist failed: {e}")

with tab[4]:
    # Reports tab: lazy import to avoid breaking other environments
    try:
        try:
            from modules.tabs.report import render_report_tab as _render_reports
        except Exception:
            from modules.tabs.reports import render_reports_tab as _render_reports  # type: ignore
        _render_reports(settings=st.session_state)
    except Exception as _e:
        st.subheader('Report')
        st.info('Reports coming soon.')
        st.caption(f'Details: {_e}')
with tab[5]:
    render_agents_tab(settings=st.session_state, has_agents=True)

with tab[6]:
    render_admin_tab(settings=st.session_state)

with tab[7]:
    render_about_tab(settings=st.session_state)

with tab[-1]:
    render_elitenewsbot_tab(settings=st.session_state)
