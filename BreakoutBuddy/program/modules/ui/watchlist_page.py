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

# === ADDED: robust render alias for app_main import ===
# app_main expects: from modules.ui.watchlist_page import render
# Accept and ignore unknown kwargs (e.g., conn), and delegate to existing functions.
try:
    # If a render already exists and accepts kwargs, leave it.
    import inspect as _inspect
    if 'render' in globals():
        _sig = _inspect.signature(render)
        if any(p.kind == p.VAR_KEYWORD for p in _sig.parameters.values()):
            pass
        else:
            raise NameError('render exists but no **kwargs; replace below')
    else:
        raise NameError('no render; define below')
except Exception:
    def render(*args, **kwargs):
        df = kwargs.get('df', None)
        symbols = kwargs.get('symbols', None)
        try:
            return render_watchlist(df=df, symbols=symbols)  # preferred
        except Exception:
            try:
                return render_watchlist(df)  # positional fallback
            except Exception:
                try:
                    return render_watchlist_tab(df)  # alt name
                except Exception:
                    return None

