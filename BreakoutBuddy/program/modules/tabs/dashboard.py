import streamlit as st
from BreakoutBuddy.program.modules.ui.explain_addenda import render_advanced_explain

# NOTE: This file is a patch helper. If your tab already has code, this block should be appended
# after your first st.dataframe(...) call to show the Explain panel.
try:
    _df = view  # common variable name in tabs
except NameError:
    _df = None
try:
    import pandas as _pd
    if isinstance(_df, _pd.DataFrame) and not _df.empty:
        _syms_series = _df.get('Ticker', _df.get('Symbol'))
        if _syms_series is not None and len(_syms_series) > 0:
            _syms = sorted(set(_syms_series.astype(str)))
            with st.expander('📝 Explain a pick (advanced)', expanded=False):
                _sym = st.selectbox('Symbol', _syms, key='explain_adv_sym_generic')
                if _sym:
                    render_advanced_explain(_sym)
except Exception:
    pass
