from __future__ import annotations
import streamlit as st
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
                st.download_button("Download scanner.csv", data=snap.to_csv(index=False).encode("utf-8"), file_name="scanner.csv")
    else:
        st.info("Set your filters and click Scan universe.")
