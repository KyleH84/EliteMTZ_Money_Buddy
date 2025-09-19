from __future__ import annotations
from pathlib import Path
import streamlit as st
import duckdb
from modules import data as data_mod
from modules import regime as regime_mod
from modules.services import enrich as enrich_svc
from modules.tabs.dashboard import render_dashboard_tab
from modules.ui.watchlist_page import render as render_watchlist_page
from modules.tabs.report import render_report_tab
from modules.tabs.agents_tab import render_agents_tab
from modules.tabs.admin import render_admin_tab
from modules.tabs.about import render_about_tab

DATA_DIR = Path(__file__).resolve().parents[2] / "Data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "breakoutbuddy.duckdb"
conn = duckdb.connect(str(DB_PATH))

try:
    from modules.tabs.sidebar import render_sidebar, SidebarSettings
    settings = render_sidebar()
except Exception:
    class SidebarSettings: pass
    settings = SidebarSettings()
    setattr(settings, "top_n", 50)
    setattr(settings, "universe_size", 300)

HAS_AGENTS = True
try:
    import modules.agents.calibration as _  # noqa
except Exception:
    HAS_AGENTS = False

st.set_page_config(page_title="BreakoutBuddy", layout="wide")
st.title("BreakoutBuddy")

tabs = st.tabs(["Dashboard", "Watchlist", "Report", "Agents", "Admin", "About"])

with tabs[0]:
    render_dashboard_tab(settings=settings, has_agents=HAS_AGENTS)

with tabs[1]:
    render_watchlist_page(
        conn=conn,
        settings=settings,
        pull_enriched_snapshot_fn=None,
        enrich_features_fn=None,
        train_online_fn=None,
        score_snapshot_fn=None,
        header=True,
    )

with tabs[2]:
    try:
        render_report_tab(
            settings=settings,
            list_universe_fn=data_mod.list_universe,
            pull_enriched_snapshot_fn=data_mod.pull_enriched_snapshot,
            enrich_features_fn=enrich_svc.enrich_features,
            compute_regime_fn=regime_mod.compute_regime,
        )
    except Exception as e:
        st.error(f"Report tab error: {e}")

with tabs[3]:
    try:
        render_agents_tab()
    except Exception as e:
        st.info(f"Agents tab unavailable: {e}")

with tabs[4]:
    try:
        render_admin_tab(settings=settings)
    except Exception as e:
        st.error(f"Admin tab error: {e}")

with tabs[5]:
    render_about_tab(data_dir=DATA_DIR, db_path=DB_PATH)
