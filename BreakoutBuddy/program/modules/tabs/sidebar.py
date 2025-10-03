from __future__ import annotations
import streamlit as st

def render_sidebar_settings():
    """Create and return app-wide settings from the sidebar.
    Only place where Universe size / Rows to display widgets are created.
    """
    # Defaults
    if 'universe_size' not in st.session_state:
        st.session_state['universe_size'] = 500
    if 'rows_to_display' not in st.session_state:
        st.session_state['rows_to_display'] = 25

    # Controls (use consistent keys; do not duplicate elsewhere)
    st.sidebar.slider('Universe size', min_value=50, max_value=5000, step=50, key='universe_size')
    st.sidebar.slider('Rows to display', min_value=5, max_value=200, step=5, key='rows_to_display')

    # Optional: a single place to show cache/storage health if desired
    try:
        from ..utilities.health_widget import render_health_widget  # type: ignore
        render_health_widget()
    except Exception:
        pass

    # Return a light settings dict for tab consumers
    return {
        'universe_size': st.session_state['universe_size'],
        'rows_to_display': st.session_state['rows_to_display'],
    }
