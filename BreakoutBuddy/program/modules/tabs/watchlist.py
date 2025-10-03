from __future__ import annotations
import inspect
import streamlit as st

# Adapter: import whichever watchlist renderer exists, then call with only the args it accepts.
def _load_impl():
    # Prefer tabs implementation first
    try:
        from .watchlist_page import render_watchlist_tab as impl  # type: ignore
        return impl
    except Exception:
        pass
    try:
        from .watchlist_page import render as impl  # type: ignore
        return impl
    except Exception:
        pass
    # Fallback to ui package
    try:
        from ..ui.watchlist_page import render_watchlist_tab as impl  # type: ignore
        return impl
    except Exception:
        pass
    try:
        from ..ui.watchlist_page import render as impl  # type: ignore
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

    # Call with only the parameters the implementation accepts
    try:
        sig = inspect.signature(impl)
        kwargs = {}
        for name, p in sig.parameters.items():
            if name == 'conn':
                kwargs['conn'] = conn
            elif name == 'settings':
                kwargs['settings'] = settings
            elif name == 'pull_enriched_snapshot_fn':
                kwargs['pull_enriched_snapshot_fn'] = pull_enriched_snapshot_fn
            elif name == 'enrich_features_fn':
                kwargs['enrich_features_fn'] = enrich_features_fn
            # Gracefully handle 'st' style legacy signatures by passing streamlit module
            elif name in ('st', 'streamlit'):
                kwargs[name] = st
        return impl(**kwargs)
    except Exception as e:
        st.error(f"Watchlist failed: {type(e).__name__}: {e}")
        return
