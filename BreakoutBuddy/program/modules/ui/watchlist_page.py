"""
Compatibility layer for callers importing from modules.ui.watchlist_page.

We re-export names from modules.tabs.watchlist_page and provide a thin
render() shim that delegates to the tabs implementation.
"""
# Re-export everything for compatibility (flake: ignore wildcards in this context)
from ..tabs.watchlist_page import *  # type: ignore F401,F403

def render(*args, **kwargs):  # type: ignore
    from ..tabs.watchlist_page import render as _render
    return _render(*args, **kwargs)
