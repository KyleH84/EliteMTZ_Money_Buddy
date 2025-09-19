# app_main.py — BreakoutBuddy (hardened, 8 tabs, dropdown quick explain, rank_now fix)
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
# ---------- end resolver ----------

# ---------- Runtime imports ----------
import duckdb
import pandas as pd
import streamlit as st

st.set_page_config(page_title="BreakoutBuddy — Smart Dashboard", page_icon="📈", layout="wide")
st.title("BreakoutBuddy")
st.caption("BB build: 2025-09-19 (hardened + tabs + dropdown + rank_now fix)")

# Core modules/services
from modules import data as data_mod
from modules import regime as regime_mod
from modules.services import enrich as enrich_svc
from modules.services import scoring as scoring_svc

# Agents (safe import for Cloud)
HAS_AGENTS = False
Orchestrator = None
_AGENT_ERR = None
try:
    from modules.services import agents_service as agents_svc
    try:
        out = agents_svc.try_import_agents()
        if isinstance(out, tuple) and len(out) >= 2:
            HAS_AGENTS, Orchestrator = bool(out[0]), out[1]
            _AGENT_ERR = out[2] if len(out) >= 3 else None
        else:
            HAS_AGENTS = bool(out)
    except Exception as _e:
        HAS_AGENTS = False
        _AGENT_ERR = _e
except Exception as _e:
    HAS_AGENTS = False
    _AGENT_ERR = _e

# Tabs & UI
from modules.tabs.sidebar import SidebarSettings, render_sidebar
from modules.tabs.dashboard import render_dashboard_tab
from modules.ui.watchlist_page import render as render_watchlist_page
from modules.tabs.report import render_report_tab
# Agents tab guarded so failures don’t crash app
try:
    from modules.tabs.agents_tab import render_agents_tab as _render_agents_tab_real
    def render_agents_tab():
        if not HAS_AGENTS:
            st.info("Agents are disabled or unavailable in this environment.")
            if _AGENT_ERR:
                st.caption(f"(agents init note: {type(_AGENT_ERR).__name__})")
            return
        try:
            _render_agents_tab_real()
        except Exception as e:
            st.info(f"Agents tab unavailable: {e}")
except Exception as _e:
    def render_agents_tab():
        st.info("Agents tab not available.")
        st.caption(f"(import note: {type(_e).__name__})")

from modules.tabs.admin import render_admin_tab
from modules.tabs.about import render_about_tab
from modules.tabs.explore import render_explore_tab
from modules.ui import plain_english as pe_ui
from modules.ui.single_ticker_analyzer import render as render_single_ticker

# ---------- DB ----------
conn = duckdb.connect(str(DB_PATH))

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

def rank_now_fn(universe_size=None, top_n: int = 25, sort_by: str | None = None,
                agent_weight: float | None = None, settings: SidebarSettings | None = None, **kwargs):
    # Build or update settings object
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
        if top_n is not None:
            try: s.top_n = int(top_n)
            except Exception: pass
        if sort_by is not None:
            try: s.sort_by = sort_by
            except Exception: pass
        if agent_weight is not None:
            try: s.agent_weight = agent_weight
            except Exception: pass

    # IMPORTANT: pass ONLY the settings object; rank_now takes 1 positional arg
    snap, regime, ranked, auc, model = scoring_svc.rank_now(s)

    # Optional resort
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
    # Dashboard renders ranked table + dropdown quick explain (in dashboard.py)
    render_dashboard_tab(
        settings=settings,
        rank_now_fn=rank_now_fn,
        friendly_lines_fn=friendly_lines_fn,
        analyze_one_fn=analyze_one_fn,
        compute_regime_fn=compute_regime_fn,
        has_agents=HAS_AGENTS,
    )

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
    render_agents_tab()

with tabs[6]:
    try:
        render_admin_tab(settings=settings)
    except Exception as e:
        st.error(f"Admin tab error: {e}")

with tabs[7]:
    render_about_tab(data_dir=DATA_DIR, db_path=DB_PATH)
