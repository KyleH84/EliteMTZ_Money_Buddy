# program/modules/tabs/admin.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List, Any, Tuple

import pandas as pd  # type: ignore
import streamlit as st

# Back-compat panel: OHLCV maintenance
from ..services.ohlcv_maint import admin_panel as ohlcv_admin_panel

# ===================== Root & Data directory resolution =====================
APP_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = APP_ROOT / "Data"


def _get_data_dir() -> Path:
    override = st.session_state.get("BB_DATA_DIR")
    if override:
        return Path(str(override)).expanduser().resolve()
    envp = os.getenv("BREAKOUTBUDDY_DATA", "").strip()
    if envp:
        try:
            return Path(envp).expanduser().resolve()
        except Exception:
            pass
    return DEFAULT_DATA_DIR.resolve()


def _set_data_dir(new_path: str) -> None:
    try:
        p = Path(new_path).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        st.session_state["BB_DATA_DIR"] = str(p)
        os.environ["BREAKOUTBUDDY_DATA"] = str(p)
        st.success(f"Data folder set to: {p}")
    except Exception as e:
        st.error(f"Failed to set data folder: {e}")


# ===================== Helpers reused by panels =====================
def _load_csv_any(names: List[str]) -> tuple[pd.DataFrame, Optional[Path]]:
    d = _get_data_dir()
    for nm in names:
        p = d / nm
        if p.exists():
            try:
                return pd.read_csv(p), p
            except Exception:
                pass
    return pd.DataFrame(), None


def _save_watchlist_snapshot(ranked: pd.DataFrame) -> None:
    d = _get_data_dir()
    try:
        wl = pd.read_csv(d / "watchlist.csv")
        if "Ticker" in wl.columns:
            wants = set(wl["Ticker"].astype(str))
            snap = ranked[ranked["Ticker"].astype(str).isin(wants)].copy()
            snap.to_csv(d / "watchlist_snapshot_latest.csv", index=False)
    except Exception:
        pass


# ===================== Panels brought back from the older Admin =====================
def _section_agents_rank():
    st.subheader("Agents & Ranking")
    try:
        from modules.agents.auto_tune import get_current_weights  # type: ignore
        w = get_current_weights()
        st.caption("Current agent weights")
        st.dataframe(w, height=160, width="stretch")
    except Exception as e:
        st.info(f"Weights unavailable: {e}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Calibrate agents (ridge on latest ranked)", use_container_width=True, key="admin_agents_calibrate"):
            try:
                from modules.agents.auto_tune import run_agents_calibration  # type: ignore
                with st.spinner("Calibrating..."):
                    rep = run_agents_calibration(lookback_days=90)
                st.success("Calibration complete.")
                st.json(rep)
            except Exception as e:
                st.error(f"Calibration failed: {e}")
    with c2:
        if st.button("Calibrate + Re-rank now (save ranked_latest.csv)", use_container_width=True, key="admin_agents_calibrate_rerank"):
            try:
                from modules.agents.auto_tune import run_agents_calibration  # type: ignore
                from modules.services.scoring import rank_now  # type: ignore
                with st.spinner("Calibrating..."):
                    _ = run_agents_calibration(lookback_days=90)
                with st.spinner("Loading base snapshot..."):
                    df, path = _load_csv_any(["ranked_latest.csv","watchlist_snapshot_latest.csv","ranked.csv","snapshot.csv"])
                if df.empty:
                    st.warning("No snapshot/ranked CSV found in Data/. Run a scan once, then try again.")
                else:
                    with st.spinner("Ranking with agents..."):
                        ranked = rank_now(df)
                    outp = _get_data_dir() / "ranked_latest.csv"
                    ranked.to_csv(outp, index=False)
                    _save_watchlist_snapshot(ranked)
                    st.success(f"Saved {outp.name} with {len(ranked)} rows.")
            except Exception as e:
                st.error(f"Re-rank failed: {e}")


def _section_llm():
    st.subheader("Local LLMs (GPT4All, .gguf)")
    st.caption("Optional. Point to a folder with .gguf models; we'll auto-pick the best instruct model.")
    try:
        from modules.services import local_llm as _llm  # type: ignore
        cfg = _llm.get_config()
        path_in = st.text_input("Model directory", value=cfg.get("model_dir",""), placeholder=r"C:\Models\GGUF   or   /mnt/models/gguf", key="llm_model_dir")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("Save path", key="llm_save_path"):
                _llm.set_model_dir(path_in); st.success("Saved path.")
        with c2:
            if st.button("Scan", key="llm_scan"):
                st.session_state["_llm_scan_models"] = _llm.list_models(path_in)
        with c3:
            if st.button("Auto-pick best now", key="llm_autopick"):
                models = st.session_state.get("_llm_scan_models", _llm.list_models(path_in))
                if models:
                    best = _llm.suggest_best_model(models)
                    if best:
                        _llm.set_preferred_model(best); st.success(f"Preferred model set to: {best}")
                else:
                    st.warning("No models found. Click Scan first.")
        with c4:
            if st.button("Clear preferred", key="llm_clear_pref"):
                _llm.set_preferred_model(""); st.success("Cleared preferred model.")
        models = st.session_state.get("_llm_scan_models", _llm.list_models(path_in))
        if models:
            ranked = _llm.rank_models(models)
            st.table({"Model": [m for m,_ in ranked], "Score": [round(s,2) for _,s in ranked]})
        st.write("Status"); st.json(_llm.status())
        if st.button("Test model (~2s)", key="llm_test_model"):
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
        from modules.services import csv_qa as qa  # type: ignore
    except Exception as e:
        st.info(f"CSV QA module unavailable: {e}")
        return
    data_root = _get_data_dir()
    files = qa.list_csvs(data_root)
    if not files:
        st.info(f"No CSVs found in {data_root}.")
        return
    options = [str(p) for p in files]
    default = next((str(p) for p in files if p.name in ("ranked_latest.csv","ranked.csv","watchlist_snapshot_latest.csv")), options[0])
    idx = options.index(default) if default in options else 0
    sel = st.selectbox("Pick a CSV", options=options, index=idx, key="csvqa_select")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Auto analyze latest", key="csvqa_auto"):
            sel = default
    with c2:
        if st.button("Analyze CSV", key="csvqa_analyze"):
            with st.spinner("Scanning..."):
                rep = qa.analyze_csv(Path(sel))
            st.json(rep)
            human = qa.summarize_for_humans(rep)
            st.markdown(f"**Summary:** {human}")
            if st.button("Explain with Local LLM (if available)", key="csvqa_llm_explain"):
                aug = qa.llm_explain(rep)
                if aug:
                    st.markdown("**Local model read**")
                    st.write(aug)
                else:
                    st.info("Local LLM not available or failed — showing rule-based summary above.")


def _section_maintenance():
    st.subheader("Maintenance — Clean build junk")
    st.caption("Removes __pycache__, *.pyc, build/dist, .pytest_cache, and egg-info inside this app folder.")
    if st.button("Clean now", key="maint_clean_now"):
        base = APP_ROOT
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


def _section_regime():
    st.subheader("Market Regime")
    try:
        from modules.regime import compute_regime  # type: ignore
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


def _section_utilities():
    st.subheader("Utilities")
    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("Scan universe now", key="util_scan_universe"):
            try:
                from modules.engines.runner import quick_scan as _scan  # type: ignore
                n = _scan(limit=500)
                st.success(f"Scan complete: {n} rows.")
            except Exception as e:
                st.error(f"Scan failed: {e}")
    with colB:
        if st.button("Health check", key="util_health_check"):
            try:
                from modules.health import run_health_check as _hc  # type: ignore
                rep = _hc()
                st.json(rep)
                st.success("Health OK." if rep.get("ok") else "Health reported issues above.")
            except Exception as e:
                st.error(f"Health check failed: {e}")
    with colC:
        try:
            from ..services.yf_diag import diag_panel  # type: ignore
            if st.button("Data diagnostics", key="util_data_diag"):
                diag_panel()
        except Exception as e:
            st.caption(f"Data diagnostics unavailable: {e}")


# ===================== New Admin layout that keeps your overrides =====================
def render_admin_tab(*, settings: Any = None):
    st.header("Admin")

    tabs = st.tabs([
        "Storage & Cache",
        "Agents & Rank",
        "Local LLMs",
        "Data QA",
        "Maintenance",
        "Market Regime",
        "Utilities",
    ])

    with tabs[0]:
        current = _get_data_dir()
        with st.expander("Data folder", expanded=False):
            st.caption("Where BreakoutBuddy reads/writes CSVs, cache, and backups.")
            st.write(f"**Current:** `{current}`")
            candidate = st.text_input("Override Data folder", value=str(current), help="Enter a full path. This folder will be created if it doesn't exist.", key="admin_data_folder_input")
            cols = st.columns([1,1])
            with cols[0]:
                if st.button("Use this folder", key="admin_data_use_folder"):
                    _set_data_dir(candidate)
                    st.experimental_rerun()
            with cols[1]:
                if st.button("Reset to default", key="admin_data_reset_default"):
                    st.session_state.pop("BB_DATA_DIR", None)
                    os.environ.pop("BREAKOUTBUDDY_DATA", None)
                    st.info(f"Reset to default: {DEFAULT_DATA_DIR}")

        # Local CSVs
        data_dir = _get_data_dir()
        try:
            csvs = sorted([p for p in data_dir.glob("*.csv") if p.is_file()])
        except Exception:
            csvs = []

        st.markdown("### Local CSVs")
        if not csvs:
            st.info(f"No CSVs found in `{data_dir}`.")
        else:
            for p in csvs[:200]:
                st.write(f"- `{p.name}`")

        st.markdown("---")
        ohlcv_admin_panel(st)

    with tabs[1]:
        _section_agents_rank()
    with tabs[2]:
        _section_llm()
    with tabs[3]:
        _section_csv_qa()
    with tabs[4]:
        _section_maintenance()
    with tabs[5]:
        _section_regime()
    with tabs[6]:
        _section_utilities()
