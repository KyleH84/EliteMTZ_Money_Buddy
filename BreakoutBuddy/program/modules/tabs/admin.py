
from __future__ import annotations
import streamlit as st
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
import pandas as pd

def _data_dir() -> Path:
    here = Path(__file__).resolve()
    for up in [here, *here.parents]:
        cand = up / "Data"
        if cand.is_dir():
            return cand
        if up.name == "modules":
            cand2 = up.parent / "Data"
            if cand2.is_dir():
                return cand2
    fb = here.parent / "Data"
    fb.mkdir(parents=True, exist_ok=True)
    return fb

def _load_csv_any(names):
    d = _data_dir()
    for nm in names:
        p = d / nm
        if p.exists():
            try:
                return pd.read_csv(p), p
            except Exception:
                pass
    return pd.DataFrame(), None

def _save_watchlist_snapshot(ranked: pd.DataFrame):
    d = _data_dir()
    try:
        wl = pd.read_csv(d / "watchlist.csv")
        if "Ticker" in wl.columns:
            wants = set(wl["Ticker"].astype(str))
            snap = ranked[ranked["Ticker"].astype(str).isin(wants)].copy()
            snap.to_csv(d / "watchlist_snapshot_latest.csv", index=False)
    except Exception:
        pass

def _section_agents_rank():
    st.subheader("Agents & Ranking")
    # Show current weights if available
    try:
        from modules.agents.auto_tune import get_current_weights, run_agents_calibration
        w = get_current_weights()
        st.caption("Current agent weights")
        st.dataframe(w, height=160, width="stretch")
    except Exception as e:
        st.info(f"Weights unavailable: {e}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Calibrate agents (ridge on latest ranked)", use_container_width=True):
            try:
                from modules.agents.auto_tune import run_agents_calibration
                with st.spinner("Calibrating…"):
                    rep = run_agents_calibration(lookback_days=90)
                st.success("Calibration complete."); st.json(rep)
            except Exception as e:
                st.error(f"Calibration failed: {e}")
    with c2:
        if st.button("Calibrate + Re-rank now (save ranked_latest.csv)", use_container_width=True):
            try:
                from modules.agents.auto_tune import run_agents_calibration
                from modules.services.scoring import rank_now
                with st.spinner("Calibrating…"):
                    _ = run_agents_calibration(lookback_days=90)
                with st.spinner("Loading base snapshot…"):
                    df, path = _load_csv_any(["ranked_latest.csv","watchlist_snapshot_latest.csv","ranked.csv","snapshot.csv"])
                if df.empty:
                    st.warning("No snapshot/ranked CSV found in Data/. Run a scan once, then try again.")
                else:
                    with st.spinner("Ranking with agents…"):
                        ranked = rank_now(df)
                    outp = _data_dir() / "ranked_latest.csv"
                    ranked.to_csv(outp, index=False)
                    _save_watchlist_snapshot(ranked)
                    st.success(f"Saved {outp.name} with {len(ranked)} rows.")
            except Exception as e:
                st.error(f"Re-rank failed: {e}")

def _section_llm():
    st.subheader("Local LLMs (GPT4All, .gguf)")
    st.caption("Optional. Point to a folder with .gguf models; we'll auto-pick the best instruct model.")
    try:
        from modules.services import local_llm as _llm
        cfg = _llm.get_config()
        path_in = st.text_input("Model directory", value=cfg.get("model_dir",""), placeholder=r"C:\\Models\\GGUF   or   /mnt/models/gguf")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("Save path"):
                _llm.set_model_dir(path_in); st.success("Saved path.")
        with c2:
            if st.button("Scan"):
                st.session_state["_llm_scan_models"] = _llm.list_models(path_in)
        with c3:
            if st.button("Auto-pick best now"):
                models = st.session_state.get("_llm_scan_models", _llm.list_models(path_in))
                if models:
                    best = _llm.suggest_best_model(models)
                    if best:
                        _llm.set_preferred_model(best); st.success(f"Preferred model set to: {best}")
                else:
                    st.warning("No models found. Click Scan first.")
        with c4:
            if st.button("Clear preferred"):
                _llm.set_preferred_model(""); st.success("Cleared preferred model.")
        models = st.session_state.get("_llm_scan_models", _llm.list_models(path_in))
        if models:
            ranked = _llm.rank_models(models)
            st.table({"Model": [m for m,_ in ranked], "Score": [round(s,2) for _,s in ranked]})
        st.write("Status"); st.json(_llm.status())
        if st.button("Test model (~2s)"):
            try:
                m = _llm.open_model()
                if m is None:
                    st.warning("No model available. Install gpt4all (pip install gpt4all) and verify folder.")
                else:
                    with m.chat_session():
                        out = m.generate("Say 'ready' in one word.", max_tokens=6, temp=0.1)
                    st.success(f"Model responded: {out!r}")
            except Exception as e:
                st.error(f"Test failed: {e}")
    except Exception as e:
        st.info(f"LLM controls unavailable: {e}")

def _section_csv_qa():
    st.subheader("Data QA (CSV)")
    try:
        from modules.services import csv_qa as qa
    except Exception as e:
        st.info(f"CSV QA module unavailable: {e}")
        return
    data_root = _data_dir()
    files = qa.list_csvs(data_root)
    if not files:
        st.info(f"No CSVs found in {data_root}.")
        return
    default = next((str(p) for p in files if p.name in ("ranked_latest.csv","ranked.csv","watchlist_snapshot_latest.csv")), str(files[0]))
    sel = st.selectbox("Pick a CSV", options=[str(p) for p in files], index=[str(p) for p in files].index(default) if files else 0)
    if st.button("Auto analyze latest"):
        sel = default
    if st.button("Analyze CSV"):
        with st.spinner("Scanning…"):
            rep = qa.analyze_csv(Path(sel))
        st.json(rep)
        human = qa.summarize_for_humans(rep)
        st.markdown(f"**Summary:** {human}")
        if st.button("Explain with Local LLM (if available)"):
            aug = qa.llm_explain(rep)
            if aug:
                st.markdown("**Local model read**")
                st.write(aug)
            else:
                st.info("Local LLM not available or failed — showing rule-based summary above.")

def _section_maintenance():
    st.subheader("Maintenance — Clean build junk")
    st.caption("Removes __pycache__, *.pyc, build/dist, .pytest_cache, and egg-info inside this app folder.")
    if st.button("Clean now"):
        base = Path(__file__).resolve().parents[3]  # BreakoutBuddy/
        patterns = [
            "**/__pycache__", "**/.pytest_cache", "**/.mypy_cache",
            "**/*.pyc", "**/*.pyo", "**/*.pyd",
            "**/build", "**/dist", "**/*.egg-info",
        ]
        removed = 0
        for pat in patterns:
            for p in base.glob(pat):
                try:
                    if p.is_dir():
                        import shutil; shutil.rmtree(p, ignore_errors=True)
                    else:
                        p.unlink(missing_ok=True)
                    removed += 1
                except Exception:
                    pass
        st.success(f"Cleanup complete. Removed ~{removed} items.")

def render_admin_tab(**kwargs):
    st.header("Admin")
    tabs = st.tabs(["Agents & Rank", "Local LLMs", "Data QA", "Maintenance"])
    with tabs[0]:
        _section_agents_rank()
    with tabs[1]:
        _section_llm()
    with tabs[2]:
        _section_csv_qa()
    with tabs[3]:
        _section_maintenance()


def _section_regime():
    st.subheader("Market Regime")
    try:
        from modules.regime import compute_regime
        reg = compute_regime()
        if isinstance(reg, dict) and reg:
            cols = st.columns(min(4, max(1, len(reg))))
            i = 0
            for k,v in reg.items():
                with cols[i % len(cols)]:
                    st.metric(k, value=str(v))
                i += 1
        else:
            st.info("No regime data available.")
    except Exception as e:
        st.info(f"Regime unavailable: {e}")

def render_admin_tab(**kwargs):
    st.header("Admin")
    tabs = st.tabs(["Agents & Rank", "Local LLMs", "Data QA", "Maintenance", "Market Regime"])
    with tabs[0]: _section_agents_rank()
    with tabs[1]: _section_llm()
    with tabs[2]: _section_csv_qa()
    with tabs[3]: _section_maintenance()
    with tabs[4]: _section_regime()


    # Extra tools
    st.subheader("Utilities")
    colA, colB = st.columns(2)
    with colA:
        if st.button("Scan universe now"):
            try:
                from modules.engines.runner import quick_scan as _scan
                n = _scan(limit=500)
                st.success(f"Scan complete: {n} rows.")
            except Exception as e:
                st.error(f"Scan failed: {e}")
    with colB:
        if st.button("Health check"):
            try:
                from modules.health import run_health_check as _hc
                rep = _hc()
                st.json(rep)
                st.success("Health OK." if rep.get("ok") else "Health reported issues above.")
            except Exception as e:
                st.error(f"Health check failed: {e}")
