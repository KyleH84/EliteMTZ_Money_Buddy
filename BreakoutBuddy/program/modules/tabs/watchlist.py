from __future__ import annotations
import inspect
import streamlit as st

def _load_impl():
    try:
        from .watchlist_page import render_watchlist_tab as impl  # tabs form
        return impl
    except Exception:
        pass
    try:
        from .watchlist_page import render as impl  # tabs legacy
        return impl
    except Exception:
        pass
    try:
        from ..ui.watchlist_page import render_watchlist_tab as impl  # ui form
        return impl
    except Exception:
        pass
    try:
        from ..ui.watchlist_page import render as impl  # ui legacy
        return impl
    except Exception:
        pass
    raise ImportError("No watchlist renderer found in tabs.watchlist_page or ui.watchlist_page")

def render_watchlist_tab(*, conn=None, settings=None, pull_enriched_snapshot_fn=None, enrich_features_fn=None):
    try:
        impl = _load_impl()
    except Exception as e:
        st.error(f"Watchlist: renderer not found: {e}")
        return

    try:
        sig = inspect.signature(impl)
        kwargs = {}
        for name in sig.parameters.keys():
            if name == 'conn': kwargs['conn'] = conn
            elif name == 'settings': kwargs['settings'] = settings
            elif name == 'pull_enriched_snapshot_fn': kwargs['pull_enriched_snapshot_fn'] = pull_enriched_snapshot_fn
            elif name == 'enrich_features_fn': kwargs['enrich_features_fn'] = enrich_features_fn
            elif name in ('st','streamlit'): kwargs[name] = st
        return impl(**kwargs)
    except Exception as e:
        st.error(f"Watchlist failed: {type(e).__name__}: {e}")
        return
