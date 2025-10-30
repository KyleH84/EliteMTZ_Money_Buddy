# === ADDED: Advanced Explain integration (Elliott Wave / Fib / Heikin Ashi) ===
try:
    import streamlit as st
    import pandas as pd
    from BreakoutBuddy.program.modules.ui.explain_addenda import render_advanced_explain
    def _ensure_explain_panel(df: pd.DataFrame):
        if df is None or df.empty:
            return
        syms = sorted(set(df.get("Ticker", df.get("Symbol", pd.Series([], dtype=str)))).astype(str))
        if not syms:
            return
        with st.expander("📝 Explain a pick (advanced)", expanded=False):
            sym = st.selectbox("Symbol", syms, key="explain_adv_sym")
            if sym:
                render_advanced_explain(sym)
    # Try to run at import time only if a module-level df is present; otherwise harmless.
except Exception:
    pass
