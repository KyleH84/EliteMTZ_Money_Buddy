from __future__ import annotations
from pathlib import Path

# ---------- Strict per-app Data/Extras resolver (BreakoutBuddy) ----------
from pathlib import Path
import os, sys
BB_HERE     = Path(__file__).resolve()
BB_APP_ROOT = BB_HERE.parents[1]   # .../BreakoutBuddy

def _bb_cloud_roots():
    h = Path.home()
    return [
        h / "OneDrive",
        h / "OneDrive - Personal",
        h / "OneDrive - Wagstaff Law Firm",
        h / "Dropbox",
        h / "Google Drive",
        h / "Library" / "CloudStorage" / "OneDrive",
        h / "Library" / "CloudStorage" / "Dropbox",
        h / "Library" / "CloudStorage" / "GoogleDrive",
    ]

def _bb_first_existing(paths):
    for p in paths:
        try:
            p2 = Path(p).expanduser().resolve()
            if p2.exists():
                return p2
        except Exception:
            pass
    return None

def bb_resolve_dir(preferred_env_var: str, fallback_name: str):
    """
    Strict per-app order (NO repo-level fallback):
      1) Env var (abs or relative)
      2) BB_APP_ROOT/<name>
      3) CWD/<name>
      4) Cloud roots: <BreakoutBuddy>/<name>
      5) Create BB_APP_ROOT/<name>
    """
    envv = os.environ.get(preferred_env_var, "").strip()
    if envv:
        cand = (Path(envv) if os.path.isabs(envv) else (Path.cwd() / envv))
        if cand.exists():
            return cand.resolve()

    hit = _bb_first_existing([BB_APP_ROOT / fallback_name, Path.cwd() / fallback_name])
    if hit:
        return hit

    cands = []
    for root in _bb_cloud_roots():
        cands += [
            root / BB_APP_ROOT.name / fallback_name,
            root / "Projects" / BB_APP_ROOT.name / fallback_name,
        ]
    hit = _bb_first_existing(cands)
    if hit:
        return hit

    target = (BB_APP_ROOT / fallback_name).resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target

BB_DATA   = bb_resolve_dir("BREAKOUTBUDDY_DATA",   "Data")
BB_EXTRAS = bb_resolve_dir("BREAKOUTBUDDY_EXTRAS", "extras")

bb_extras_src = (BB_EXTRAS / "src")
if bb_extras_src.exists() and str(bb_extras_src) not in sys.path:
    sys.path.insert(0, str(bb_extras_src))
# ---------- end resolver ----------
import streamlit as st
from pathlib import Path as _DBG_P
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


from pathlib import Path as _P

def _resolve_data_dir_app():
    here = _P(__file__).resolve()
    candidates = [
        here.parents[2] / "Data",          # BreakoutBuddy/Data  (repo-level)
        here.parent / "Data",              # BreakoutBuddy/program/Data
        here.parents[3] / "Data",          # extra-safe: one more up
        _P.cwd() / "Data",                 # current working dir/Data
    ]
    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:
            pass
    return candidates[0]

DATA_DIR = _resolve_data_dir_app()
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / str(BB_DATA / 'breakoutbuddy.duckdb')
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

st.sidebar.expander("Debug: DATA_DIR").write({
    "DATA_DIR": str(DATA_DIR),
    "exists": DATA_DIR.exists(),
})

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
