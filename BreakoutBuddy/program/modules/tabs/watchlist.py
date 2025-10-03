from __future__ import annotations
import inspect
import importlib
import streamlit as st

def _load_watchlist_module():
    # Try tabs page first, then ui shim
    for modname in [
        "BreakoutBuddy.program.modules.tabs.watchlist_page",
        "BreakoutBuddy.program.modules.ui.watchlist_page",
    ]:
        try:
            return importlib.import_module(modname)
        except Exception:
            continue
    raise ImportError("Could not locate watchlist_page module in tabs/ or ui/.")

def render_watchlist_tab(*, conn=None, settings=None, pull_enriched_snapshot_fn=None, enrich_features_fn=None):
    try:
        mod = _load_watchlist_module()
    except Exception as e:
        st.error(f"Watchlist module not found: {e}")
        return

    func = getattr(mod, "render_watchlist_tab", None) or getattr(mod, "render", None)
    if func is None:
        st.error("Watchlist: neither 'render_watchlist_tab' nor 'render' is defined in watchlist_page.")
        return

    # Pass only kwargs the impl accepts
    try:
        sig = inspect.signature(func)
        kwargs = {}
        for name in sig.parameters.keys():
            if name == 'conn': kwargs['conn'] = conn
            elif name == 'settings': kwargs['settings'] = settings
            elif name == 'pull_enriched_snapshot_fn': kwargs['pull_enriched_snapshot_fn'] = pull_enriched_snapshot_fn
            elif name == 'enrich_features_fn': kwargs['enrich_features_fn'] = enrich_features_fn
            elif name in ('st','streamlit'): kwargs[name] = st
        return func(**kwargs)
    except Exception as e:
        st.error(f"Watchlist failed to render: {type(e).__name__}: {e}")
        return
