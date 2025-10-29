from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from .. import watchlist as wlmod


def render_watchlist(df: Optional[pd.DataFrame], *, header: bool = True) -> Optional[pd.DataFrame]:
    if header:
        st.header("Watchlist")

    wl = wlmod.read_watchlist()

    with st.expander("Manage watchlist", expanded=True):
        new = st.text_input("Add ticker", placeholder="e.g. NVDA, AAPL").strip().upper()
        if st.button("Add"):
            if new:
                wlmod.add_to_watchlist(new)
                st.success(f"Added {new} to watchlist")
                wl = wlmod.read_watchlist()
            else:
                st.info("Enter a ticker symbol before adding.")

        to_remove = st.multiselect("Remove tickers", wl)
        if st.button("Remove selected"):
            if to_remove:
                wlmod.remove_from_watchlist(to_remove)
                st.success(f"Removed: {', '.join(to_remove)}")
                wl = wlmod.read_watchlist()
            else:
                st.info("Choose one or more tickers to remove.")

    if not wl:
        st.info("Watchlist is empty. Add tickers above to get started.")
        return None

    table = pd.DataFrame({"Ticker": [str(t).strip().upper() for t in wl]})
    if df is not None and not df.empty and "Ticker" in df.columns:
        table = table.merge(df, on="Ticker", how="left")

    if "Ticker" in table.columns:
        table = table.drop_duplicates(subset=["Ticker"], keep="last")

    st.dataframe(table, use_container_width=True, hide_index=True)
    return table


def render(*, conn=None, settings=None, enrich_features_fn=None, header: bool = True, **_kwargs):
    df: Optional[pd.DataFrame] = None
    tickers = wlmod.read_watchlist()
    if tickers:
        try:
            df = wlmod.enriched_snapshot(tickers, enrich_features_fn=enrich_features_fn)
        except Exception as exc:
            st.warning(f"Unable to enrich watchlist data: {exc}")
    return render_watchlist(df, header=header)
