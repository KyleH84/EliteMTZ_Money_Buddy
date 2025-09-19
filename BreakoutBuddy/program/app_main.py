# app_main.py — BreakoutBuddy (tabs restored + dropdown Quick Actions + safe paths)
from __future__ import annotations
from pathlib import Path
import os, sys

# ---------- Minimal, app-root-only resolver ----------
HERE = Path(__file__).resolve()

def _find_program_dir(start: Path) -> Path:
    p = start
    for _ in range(6):
        if p.name.lower() == "program":
            return p
        if (p / "program").is_dir():
            return (p / "program")
        p = p.parent
    return start.parent

PROGRAM_DIR = _find_program_dir(HERE)
APP_ROOT    = PROGRAM_DIR.parent
MODULES_DIR = Path(os.environ.get("BREAKOUTBUDDY_MODULES_DIR", str(PROGRAM_DIR / "modules"))).resolve()
TABS_DIR    = Path(os.environ.get("BREAKOUTBUDDY_TABS_DIR",     str(MODULES_DIR / "tabs"))).resolve()

for p in [str(MODULES_DIR), str(PROGRAM_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

DATA_DIR   = Path(os.environ.get("BREAKOUTBUDDY_DATA",   str(APP_ROOT / "Data"))).resolve()
EXTRAS_DIR = Path(os.environ.get("BREAKOUTBUDDY_EXTRAS", str(APP_ROOT / "extras"))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXTRAS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "breakoutbuddy.duckdb"

# ---------- Runtime imports ----------
import duckdb
import pandas as pd
import streamlit as st

# Modules / services
from modules import data as data_mod
from modules import regime as regime_mod
from modules.services import enrich as enrich_svc
from modules.services import scoring as scoring_svc
from modules.services import agents_service as agents_svc

# Tabs & UI
from modules.tabs.sidebar import SidebarSettings, render_sidebar
from modules.tabs.dashboard import render_dashboard_tab
from modules.ui.watchlist_page import render as render_watchlist_page
from modules.tabs.report import render_report_tab
from modules.tabs.agents_tab import render_agents_tab
from modules.tabs.admin import render_admin_tab
from modules.tabs.about import render_about_tab
from modules.tabs.explore import render_explore_tab
from modules.ui import plain_english as pe_ui
from modules.ui.single_ticker_analyzer import render as render_single_ticker

# ---------- App setup ----------
st.set_page_config(page_title="BreakoutBuddy — Smart Dashboard", page_icon="📈", layout="wide")
st.title("BreakoutBuddy")

conn = duckdb.connect(str(DB_PATH))
HAS_AGENTS, Orchestrator, _AGENT_ERR = agents_svc.try_import_agents()

# ---------- Thin wrappers used by tabs ----------
def list_universe_fn(n: int):
    return data_mod.list_universe(n)

def pull_enriched_snapshot_fn(tickers):
    return data_mod.pull_enriched_snapshot(tickers)

def enrich_features_fn(tickers, base_df: pd.DataFrame | None = None):
    return enrich_svc.enrich_features(tickers, base_df)

def friendly_lines_fn(row: pd.Series):
    try:
        return pe_ui.friendly_lines(pd.Series(row))
    except Exception:
        return []

def analyze_one_fn(ticker: str = "", *, model=None, prior: float | None = None, **kwargs) -> pd.DataFrame:
    if prior is None:
        prior = kwargs.pop("prior_from", None)
    if prior is None:
        prior = 0.50
    try:
        return scoring_svc.analyze_one((ticker or "").upper(), model=model, prior=prior)
    except TypeError:
        return scoring_svc.analyze_one((ticker or "").upper())
    except Exception:
        return pd.DataFrame()

def compute_regime_fn() -> dict:
    return regime_mod.compute_regime()

def rank_now_fn(universe_size=None, top_n: int = 25, sort_by: str | None = None, agent_weight: float | None = None, settings: SidebarSettings | None = None, **kwargs):
    if settings is None:
        class _S: pass
        s = _S()
        setattr(s, "universe_size", int(universe_size) if universe_size is not None else 300)
        setattr(s, "top_n", int(top_n))
        setattr(s, "sort_by", sort_by)
        setattr(s, "agent_weight", agent_weight)
    else:
        s = settings
        if universe_size is not None:
            try: s.universe_size = int(universe_size)
            except Exception: pass
    snap, regime, ranked, auc, model = scoring_svc.rank_now(s, int(top_n))
    if sort_by:
        try:
            ranked = scoring_svc.apply_sort(ranked, sort_by)
        except Exception:
            pass
    return snap, regime, ranked, auc, model

# ---------- Sidebar ----------
settings = render_sidebar(default_universe=300, default_topn=25, default_agent_weight=0.30, has_agents=HAS_AGENTS)

# ---------- Tabs ----------
tabs = st.tabs(["Dashboard", "Single", "Explore", "Watchlist", "Report", "Agents", "Admin", "About"])

with tabs[0]:
    # Hide built-in "Quick Actions" button wall (non-destructive CSS)
    st.markdown(
        """
        <style>
        div:has(> div > p:contains('Quick Actions')) + div { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Render stock dashboard (table, metrics, etc.)
    render_dashboard_tab(
        settings=settings,
        rank_now_fn=rank_now_fn,
        friendly_lines_fn=friendly_lines_fn,
        analyze_one_fn=analyze_one_fn,
        compute_regime_fn=compute_regime_fn,
        has_agents=HAS_AGENTS,
    )

    # Our dropdown Quick Action (safe duplicate, lightweight)
    try:
        # Run a small rank to get ticker list for dropdown (matches table order)
        _, _, ranked_for_dropdown, _, _ = rank_now_fn(
            universe_size=getattr(settings, "universe_size", 300),
            top_n=getattr(settings, "top_n", 25),
            sort_by=getattr(settings, "sort_by", None),
            agent_weight=getattr(settings, "agent_weight", 0.30),
            settings=settings,
        )
        options = ranked_for_dropdown["Ticker"].astype(str).tolist() if not ranked_for_dropdown.empty and "Ticker" in ranked_for_dropdown.columns else []
        if options:
            st.markdown("### Quick explain")
            sel = st.selectbox("Explain which ticker?", options, index=0, key="bb_quick_explain_sel")
            row = ranked_for_dropdown.loc[ranked_for_dropdown["Ticker"].astype(str) == sel].iloc[0]
            lines = friendly_lines_fn(row)
            for ln in lines:
                st.markdown(f"- {ln}")
    except Exception:
        pass

with tabs[1]:
    render_single_ticker(
        settings=settings,
        analyze_one_fn=analyze_one_fn,
        friendly_lines_fn=friendly_lines_fn,
        header=True,
    )

with tabs[2]:
    render_explore_tab(
        settings=settings,
        list_universe_fn=list_universe_fn,
        pull_enriched_snapshot_fn=pull_enriched_snapshot_fn,
        enrich_features_fn=enrich_features_fn,
    )

with tabs[3]:
    conn = duckdb.connect(str(DB_PATH))
    render_watchlist_page(
        conn=conn,
        settings=settings,
        pull_enriched_snapshot_fn=pull_enriched_snapshot_fn,
        enrich_features_fn=enrich_features_fn,
        train_online_fn=None,
        score_snapshot_fn=None,
        header=True,
    )

with tabs[4]:
    try:
        render_report_tab(
            settings=settings,
            list_universe_fn=list_universe_fn,
            pull_enriched_snapshot_fn=pull_enriched_snapshot_fn,
            enrich_features_fn=enrich_features_fn,
            compute_regime_fn=compute_regime_fn,
        )
    except Exception as e:
        st.error(f"Report tab error: {e}")

with tabs[5]:
    try:
        render_agents_tab()
    except Exception as e:
        st.info(f"Agents tab unavailable: {e}")

with tabs[6]:
    try:
        render_admin_tab(settings=settings)
    except Exception as e:
        st.error(f"Admin tab error: {e}")

with tabs[7]:
    render_about_tab(data_dir=DATA_DIR, db_path=DB_PATH)
