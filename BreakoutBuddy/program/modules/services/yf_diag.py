from __future__ import annotations
import traceback, datetime as dt
from typing import Dict, Any

def _result(status: str, **kw) -> Dict[str, Any]:
    out = {'status': status, 'ts': dt.datetime.utcnow().isoformat() + 'Z'}
    out.update(kw)
    return out

def probe_yfinance() -> Dict[str, Any]:
    try:
        import yfinance as yf
    except Exception as e:
        return _result('IMPORT_ERROR', error=str(e), tb=traceback.format_exc())
    info = {'yfinance_version': getattr(yf, '__version__', 'unknown')}
    try:
        df = yf.download('SPY', period='1mo', interval='1d', progress=False, threads=False)
        empty = df is None or getattr(df, 'empty', True)
        info['download_empty'] = bool(empty)
        if not empty:
            info['download_rows'] = int(getattr(df, 'shape', (0, 0))[0])
            info['download_cols'] = int(getattr(df, 'shape', (0, 0))[1])
            last = df.tail(1)
            info['download_last_index'] = str(getattr(last, 'index', [''])[-1]) if hasattr(last, 'index') else ''
        else:
            info['download_rows'] = 0
            info['download_cols'] = 0
    except Exception as e:
        info['download_exception'] = str(e)
        info['download_tb'] = traceback.format_exc()
    try:
        tk = yf.Ticker('SPY')
        hist = tk.history(period='5d', interval='1d', auto_adjust=False)
        info['ticker_empty'] = bool(hist is None or getattr(hist, 'empty', True))
        if not info['ticker_empty']:
            info['ticker_rows'] = int(hist.shape[0])
            info['ticker_last_index'] = str(hist.tail(1).index[-1])
    except Exception as e:
        info['ticker_exception'] = str(e)
        info['ticker_tb'] = traceback.format_exc()
    if info.get('download_exception') and info.get('ticker_exception'):
        return _result('NETWORK_OR_REMOTE_ERROR', **info)
    if info.get('download_empty') and info.get('ticker_empty'):
        return _result('EMPTY_DATA', **info)
    return _result('OK', **info)

def diag_panel():
    import streamlit as st, json
    st.subheader('Data Diagnostics: yfinance')
    if st.button('Run yfinance probe', type='primary'):
        res = probe_yfinance()
        st.code(json.dumps(res, indent=2), language='json')
        status = res.get('status')
        if status == 'OK':
            st.success('yfinance looks good. If tables are still constant, disable Demo Mode and rebuild caches.')
        elif status in ('EMPTY_DATA',):
            st.warning('yfinance returned empty data. Common reasons:\n- Invalid tickers or empty universe\n- Weekend/holiday + strict freshness gate\n- Temporary throttling (reduce batch size / retry)')
        elif status in ('NETWORK_OR_REMOTE_ERROR', 'IMPORT_ERROR'):
            st.error('Cannot import or reach yfinance. Check requirements.txt, network egress, or temporary Yahoo issues.')
