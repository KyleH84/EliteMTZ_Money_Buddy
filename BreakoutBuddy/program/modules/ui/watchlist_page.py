import streamlit as st
from BreakoutBuddy.program.utilities.feature_fixups import ensure_basic_indicators
import pandas as pd
from .. import watchlist as wlmod
from ..services.enrich import ensure_features  # fill missing indicators

def render_watchlist(df: pd.DataFrame | None = None, **kwargs):
    """
    Watchlist UI. Accepts df and arbitrary **kwargs (e.g., conn) for back-compat.
    Unknown kwargs are ignored so older call sites keep working.
    """
    if df is None:
        df = pd.DataFrame()
    df = ensure_basic_indicators(df)

    st.header("Watchlist")

    with st.expander("Manage watchlist", expanded=True):
        new = st.text_input("Add ticker").strip().upper()
        if st.button("Add"):
            if new:
                try:
                    # Prefer dedicated methods if they exist
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

    # Drop duplicate tickers and fill indicators
    if df is not None and not df.empty and "Ticker" in df.columns:
        df = df.drop_duplicates(subset=["Ticker"], keep="last")
        df = ensure_features(df)  # <- compute/fill RelSPY, RSI4, ConnorsRSI, RVOL, P_up, SqueezeHint, etc.

    st.dataframe(df, use_container_width=True, hide_index=True)

# Back-compat for callers importing render()
def render(*args, **kwargs):
    df = kwargs.pop("df", None)
    if df is None and len(args) >= 1:
        df = args[0]
    # Ignore other kwargs (e.g., conn)
    return render_watchlist(df=df, **kwargs)
