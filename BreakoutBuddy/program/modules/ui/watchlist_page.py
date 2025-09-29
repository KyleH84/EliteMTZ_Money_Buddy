from __future__ import annotations
import streamlit as st
import pandas as pd
from ..utilities.watchlist_store import load_watchlist, save_watchlist
from ..modules.features import ensure_basic_indicators

def render_watchlist_page() -> None:
    st.subheader("Watchlist")
    wl = load_watchlist()
    tickers = sorted(set(wl or []))
    with st.form("watchlist_form", clear_on_submit=True):
        new = st.text_input("Add ticker", placeholder="AAPL")
        submitted = st.form_submit_button("Add")
        if submitted and new:
            tickers.append(new.strip().upper())
            tickers = sorted(set(tickers))
            save_watchlist(tickers)
            st.success(f"Added {new.strip().upper()}")
    if tickers:
        df = pd.DataFrame({"symbol": tickers})
        df = ensure_basic_indicators(df)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Your watchlist is empty.")
