import streamlit as st
import pandas as pd
from .. import watchlist as wlmod

def render_watchlist(df: pd.DataFrame):
    st.header("Watchlist")

    with st.expander("Manage watchlist", expanded=True):
        new = st.text_input("Add ticker").strip().upper()
        if st.button("Add"):
            if new:
                try:
                    if hasattr(wlmod, "add_to_watchlist"):
                        wlmod.add_to_watchlist(new)
                    else:
                        wlmod.write_watchlist(list(set(wlmod.read_watchlist() + [new])))
                    st.success(f"Added {new} to watchlist")
                except Exception as e:
                    st.error(f"Failed to add: {e}")

        try:
            existing = wlmod.read_watchlist()
        except Exception:
            existing = []

        to_remove = st.multiselect("Remove tickers", existing)
        if st.button("Remove selected"):
            try:
                if hasattr(wlmod, "remove_from_watchlist"):
                    for t in to_remove:
                        wlmod.remove_from_watchlist(t)
                else:
                    keep = [t for t in existing if t not in set(to_remove)]
                    wlmod.write_watchlist(keep)
                st.success(f"Removed: {', '.join(to_remove)}")
            except Exception as e:
                st.error(f"Failed to remove: {e}")

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

    if df is not None and not df.empty and 'Ticker' in df.columns:
        df = df.drop_duplicates(subset=['Ticker'], keep='last')

    st.dataframe(df, use_container_width=True, hide_index=True)

# Back-compat for callers importing render()
def render(df: pd.DataFrame):
    return render_watchlist(df)
