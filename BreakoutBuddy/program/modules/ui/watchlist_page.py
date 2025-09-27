import streamlit as st
import pandas as pd
from .. import watchlist as wlmod

def render_watchlist(df: pd.DataFrame | None = None, **kwargs):
    """
    Watchlist UI. Accepts df and arbitrary **kwargs (e.g., conn) for back-compat.
    Unknown kwargs are ignored so older call sites keep working.
    """
    if df is None:
        df = pd.DataFrame()

    st.header("Watchlist")

    with st.expander("Manage watchlist", expanded=True):
        new = st.text_input("Add ticker").strip().upper()
        if st.button("Add"):
            if new:
                try:
                    if hasattr(wlmod, "add_to_watchlist"):
                        wlmod.add_to_watchlist(new)
                    else:
                        existing = wlmod.read_watchlist()
                        wlmod.write_watchlist(list(set(existing + [new])))
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

    # Ensure every watchlist ticker appears in the table
    try:
        wl = wlmod.read_watchlist()
        if isinstance(wl, (list, tuple)) and wl:
            _all = pd.DataFrame({"Ticker": [str(t).strip().upper() for t in wl]})
            if df is None or df.empty or "Ticker" not in df.columns:
                df = _all
            else:
                df = _all.merge(df, on="Ticker", how="left")
    except Exception:
        pass

    # Drop duplicate tickers if any and keep the newest row
    if df is not None and not df.empty and "Ticker" in df.columns:
        df = df.drop_duplicates(subset=["Ticker"], keep="last")

    st.dataframe(df, use_container_width=True, hide_index=True)

# Back-compat: accept positional/keyword args like (df, conn=..., *args)
def render(*args, **kwargs):
    df = None
    if "df" in kwargs:
        df = kwargs.pop("df")
    elif len(args) >= 1:
        df = args[0]
    # Ignore any other kwargs (e.g., conn) to maintain compatibility
    return render_watchlist(df=df, **kwargs)
