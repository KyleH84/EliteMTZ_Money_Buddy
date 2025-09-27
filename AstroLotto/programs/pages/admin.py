from __future__ import annotations

"""
Adapter for the AstroLotto admin page.

The original AstroLotto repository includes an admin interface at
``AstroLotto/programs/admin.py`` but the Streamlit router expects the
module to live under ``programs/pages/admin.py`` and expose a
``render()`` function.  This thin wrapper imports and reloads the
original admin module so that its top‑level Streamlit code executes
whenever the admin page is selected.  Using ``importlib.reload``
ensures that repeated visits to the page refresh its state rather than
relying on stale cached imports.
"""

import importlib
import streamlit as st


def render() -> None:
    """Render the AstroLotto admin page by delegating to the original module."""
    try:
        # Import the original admin module.  It may have already been imported
        # earlier in the Streamlit session, so we reload it to re‑execute its
        # top‑level code and update the UI accordingly.
        import AstroLotto.programs.admin as admin_module  # type: ignore
        importlib.reload(admin_module)
    except Exception as e:
        st.error(f"Failed to load AstroLotto admin page: {e}")