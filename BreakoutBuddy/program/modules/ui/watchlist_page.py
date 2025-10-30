import streamlit as st
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

    st.dataframe(df, use_container_width=True, hide_index=True)


# --- Back-compat alias for app_main import ---
# app_main imports: from modules.ui.watchlist_page import render
try:
    render  # type: ignore[name-defined]
except NameError:
    def render(df=None):
        try:
            return render_watchlist(df)  # call existing function if present
        except Exception:
            # Try common alternates if names differ
            try:
                return render_watchlist_tab(df)
            except Exception:
                return None
