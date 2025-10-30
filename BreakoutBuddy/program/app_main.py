
# === ADDED: sidebar glossary ===
try:
    from BreakoutBuddy.program.modules.ui.glossary import render_glossary as _bb_render_glossary
    import streamlit as st as _bb_st
    with _bb_st.sidebar.expander("📘 Glossary", expanded=False):
        _bb_render_glossary()
except Exception as _e:
    # non-fatal if sidebar not available in this context
    pass
