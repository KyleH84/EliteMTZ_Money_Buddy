from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import streamlit as st
from BreakoutBuddy.program.modules.ui.explain_addenda import render_advanced_explain
import pandas as pd

def render_scanner_tab(
    *,
    settings,
    list_universe_fn,
    pull_enriched_snapshot_fn,
    enrich_features_fn,
    train_online_fn=None,
    score_snapshot_fn=None,
):
    st.subheader("Universe Scanner")
    rsi_min = st.number_input("Min RSI4", value=10.0, step=1.0)
    rsi_max = st.number_input("Max RSI4", value=90.0, step=1.0)
    rvol_min = st.number_input("Min RVOL", value=1.2, step=0.1)

    if st.button("Scan universe", key="scan_universe", type="primary"):
        with st.spinner("Pulling snapshot…"):
            try:
                try:
                    syms = list_universe_fn(settings.universe_size)
                except TypeError:
                    syms = list_universe_fn(n=settings.universe_size)
                snap = pull_enriched_snapshot_fn(syms)
            except Exception as e:
                st.error(f"Failed to pull snapshot: {e}")
            else:
                needed = ["RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint","ChangePct","P_up"]
                if any(c not in snap.columns for c in needed):
                    try:
                        snap = enrich_features_fn(list(snap.get("Ticker").astype(str)), snap)
                    except Exception:
                        pass
                if "RSI4" in snap.columns:
                    snap = snap[(snap["RSI4"]>=rsi_min) & (snap["RSI4"]<=rsi_max)]
                if "RVOL" in snap.columns:
                    snap = snap[snap["RVOL"]>=rvol_min]
                st.caption(f"Rows: {len(snap)}")
                cols = [c for c in ["Ticker","Close","ChangePct","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint","P_up"] if c in snap.columns]
                st.dataframe(snap[cols] if cols else snap, width="stretch", hide_index=True)

    # === ADDED: Advanced Explain (Elliott Wave / Fib / Heikin Ashi) ===
    try:
        _tmp_df_for_explain = snap[cols] if cols else snap
        import pandas as _pd
        if isinstance(_tmp_df_for_explain, _pd.DataFrame) and not _tmp_df_for_explain.empty:
            _syms_series = _tmp_df_for_explain.get("Ticker", _tmp_df_for_explain.get("Symbol"))
            if _syms_series is not None and len(_syms_series) > 0:
                _syms = sorted(set(_syms_series.astype(str)))
                with st.expander("📝 Explain a pick (advanced)", expanded=False):
                    _sym = st.selectbox("Symbol", _syms, key="explain_adv_sym_-2359558414944383004")
                    if _sym:
                        render_advanced_explain(_sym)
    except Exception:
        pass
                st.download_button("Download scanner.csv", data=snap.to_csv(index=False).encode("utf-8"), file_name="scanner.csv")
    else:
        st.info("Set your filters and click Scan universe.")
