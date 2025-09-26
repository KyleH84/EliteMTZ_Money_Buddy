# program/modules/tabs/agents.py
from __future__ import annotations
import os, traceback
from pathlib import Path
from typing import Any
import pandas as pd  # type: ignore
import streamlit as st

APP_ROOT = Path(__file__).resolve().parents[3]
def _get_data_dir() -> Path:
    override = st.session_state.get("BB_DATA_DIR")
    if override: return Path(str(override)).expanduser().resolve()
    envp = os.getenv("BREAKOUTBUDDY_DATA", "").strip()
    if envp:
        try: return Path(envp).expanduser().resolve()
        except Exception: pass
    return (APP_ROOT / "Data").resolve()

def render_agents_tab(*, settings: Any = None, has_agents: bool = True, **_kwargs):
    st.header("Agents")
    data_dir = _get_data_dir()
    st.caption(f"Data folder: `{data_dir}`")

    err = None
    try:
        from modules.agents.auto_tune import get_current_weights, run_agents_calibration  # type: ignore
    except Exception as e:
        err = f"auto_tune import failed: {e}\n{traceback.format_exc()}"
    try:
        from modules.services.scoring import rank_now  # type: ignore
    except Exception as e:
        rank_now = None  # type: ignore
        if err is None: err = f"scoring import failed: {e}\n{traceback.format_exc()}"

    if err and 'auto_tune' in err:
        st.error("Agents are disabled or unavailable in this environment.")
        with st.expander("Details", expanded=False):
            st.code(err)
        st.markdown(
            "- Ensure `program/modules/agents/auto_tune.py` exists.\n"
            "- Install any extra dependencies required by your agents."
        )
        return

    try:
        w = get_current_weights()  # type: ignore
        st.subheader("Current weights")
        st.dataframe(w, height=160, width="stretch")
    except Exception as e:
        st.info(f"Weights unavailable: {e}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Calibrate agents (ridge on latest ranked)", use_container_width=True, key="agents_tab_calibrate"):
            try:
                rep = run_agents_calibration(lookback_days=90)  # type: ignore
                st.success("Calibration complete."); st.json(rep)
            except Exception as e:
                st.error(f"Calibration failed: {e}")
    with col2:
        if st.button("Calibrate + Re-rank now (save ranked_latest.csv)", use_container_width=True, key="agents_tab_rerank"):
            try:
                pick = None
                for nm in ("ranked_latest.csv","watchlist_snapshot_latest.csv","ranked.csv","snapshot.csv"):
                    p = data_dir / nm
                    if p.exists(): pick = p; break
                if not pick:
                    st.warning("No snapshot/ranked CSV found in Data/. Run a scan once, then try again.")
                    return
                if rank_now is None:
                    st.warning("Ranking function unavailable; calibration ran but cannot re-rank in this environment.")
                    return
                df = pd.read_csv(pick)
                ranked = rank_now(df)  # type: ignore
                outp = data_dir / "ranked_latest.csv"
                ranked.to_csv(outp, index=False)
                st.success(f"Saved {outp.name} with {len(ranked)} rows.")
            except Exception as e:
                st.error(f"Re-rank failed: {e}")
