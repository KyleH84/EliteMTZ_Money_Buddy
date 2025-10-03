"""Compatibility layer: expose `render()` for older callers.

Tries tabs.watchlist_page.render first; if missing, falls back to
tabs.watchlist_page.render_watchlist_tab.
"""
from __future__ import annotations

# Re-export public names from tabs version
from ..tabs.watchlist_page import *  # type: ignore F401,F403

def render(*args, **kwargs):  # type: ignore
    try:
        from ..tabs.watchlist_page import render as _impl
    except Exception:
        from ..tabs.watchlist_page import render_watchlist_tab as _impl  # type: ignore
    return _impl(*args, **kwargs)
