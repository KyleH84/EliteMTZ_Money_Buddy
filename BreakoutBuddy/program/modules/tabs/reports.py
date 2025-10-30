
# === ADDED (non-destructive): safe indicator fill + advanced explain ===
try:
    from BreakoutBuddy.program.utilities.indicator_fill_safe import safe_fill_indicators
    from BreakoutBuddy.program.modules.ui.explain_addenda import render_advanced_explain
    import pandas as _pd, streamlit as _st
    if 'view' in globals():
        try:
            view = safe_fill_indicators(view)
        except Exception:
            pass
        try:
            if isinstance(view, _pd.DataFrame) and not view.empty:
                _syms_series = view.get('Ticker', view.get('Symbol'))
                if _syms_series is not None and len(_syms_series) > 0:
                    _syms = sorted(set(_syms_series.astype(str)))
                    with _st.expander('📝 Explain a pick (advanced)', expanded=False):
                        _sym = _st.selectbox('Symbol', _syms, key='exp_adv__'+__name__)
                        if _sym:
                            render_advanced_explain(_sym)
        except Exception:
            pass
except Exception:
    pass
