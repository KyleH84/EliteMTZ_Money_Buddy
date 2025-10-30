from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import streamlit as st

# --- Unified data fill (no UI change) ---
try:
    from BreakoutBuddy.program.utilities.feature_fixups import ensure_basic_indicators
except Exception:
    ensure_basic_indicators = None

def _bb_unify(view):
    import pandas as _pd, numpy as _np
    if view is None or view.empty:
        return view
    # % +/- from ChangePct or Open/Close
    if "% +/-" not in view.columns:
        if "ChangePct" in view.columns:
            s = _pd.to_numeric(view["ChangePct"], errors="coerce")
            view["% +/-"] = s
        elif {"Open","Close"}.issubset(view.columns):
            o = _pd.to_numeric(view["Open"], errors="coerce")
            c = _pd.to_numeric(view["Close"], errors="coerce")
            view["% +/-"] = (c - o) / o * 100.0
    # Ensure indicators
    if ensure_basic_indicators is not None:
        try:
            view = ensure_basic_indicators(view)
        except Exception:
            pass
    # RiskBadge from RVOL/Volume
    if "RiskBadge" not in view.columns:
        try:
            rvol = _pd.to_numeric(view.get("RVOL", _pd.Series([], dtype=float)), errors="coerce")
            if rvol is not None and len(rvol):
                view["RiskBadge"] = rvol.apply(lambda r: "High Volume" if r>=1.5 else ("Medium Volume" if r>=1.1 else "Low Volume"))
            else:
                vol = _pd.to_numeric(view.get("Volume", _pd.Series([], dtype=float)), errors="coerce")
                view["RiskBadge"] = vol.apply(lambda v: "High Volume" if v>=1e8 else ("Medium Volume" if v>=5e7 else "Low Volume"))
        except Exception:
            pass
    # Column order
    want = ["Ticker","Open","High","Low","Close","Volume","% +/-","RSI4","ConnorsRSI","RelSPY","RVOL","ATR","PctFrom200d","SqueezeHint","RiskBadge"]
    have = [c for c in want if c in view.columns]
    if have:
        view = view[h ave]
    return view
# --- end unified data fill ---
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
                st.dataframe(_bb_unify(snap)[cols] if cols else snap, width="stretch", hide_index=True)
                st.download_button("Download scanner.csv", data=snap.to_csv(index=False).encode("utf-8"), file_name="scanner.csv")
    else:
        st.info("Set your filters and click Scan universe.")
