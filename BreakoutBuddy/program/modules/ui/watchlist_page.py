from __future__ import annotations
"""Compatibility layer for Watchlist.

Exposes `render()` for older callers and falls back to `render_watchlist_tab`
if that's the only function available.
"""
def render(*args, **kwargs):  # type: ignore
    try:
        from ..tabs.watchlist_page import render as _impl  # type: ignore
    except Exception:
        from ..tabs.watchlist_page import render_watchlist_tab as _impl  # type: ignore
    return _impl(*args, **kwargs)
