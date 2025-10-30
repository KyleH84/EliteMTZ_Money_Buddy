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
from .. import watchlist as wlmod

def render_watchlist(df: pd.DataFrame):
    st.header("Watchlist")

    with st.expander("Manage watchlist", expanded=True):
        new = st.text_input("Add ticker").strip().upper()
        if st.button("Add"):
            if new:
                wlmod.add_to_watchlist(new)
                st.success(f"Added {new} to watchlist")

        to_remove = st.multiselect("Remove tickers", wlmod.read_watchlist())
        if st.button("Remove selected"):
            for t in to_remove:
                wlmod.remove_from_watchlist(t)
            st.success(f"Removed: {', '.join(to_remove)}")

    # Ensure every watchlist ticker appears in the table
    try:
        wl = wlmod.read_watchlist()
        if isinstance(wl, (list, tuple)) and wl:
            _all = pd.DataFrame({'Ticker': [str(t).strip().upper() for t in wl]})
            if df is None or df.empty or 'Ticker' not in df.columns:
                df = _all
            else:
                df = _all.merge(df, on='Ticker', how='left')
    except Exception:
        pass

    # Drop duplicate tickers if any and keep the newest row
    if df is not None and not df.empty and 'Ticker' in df.columns:
        df = df.drop_duplicates(subset=['Ticker'], keep='last')

    st.dataframe(_bb_unify(df), use_container_width=True, hide_index=True)
