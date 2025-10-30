from __future__ import annotations
import streamlit as st
import pandas as pd, numpy as np

def _heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    ha = pd.DataFrame(index=df.index)
    ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4.0
    ha['HA_Open'] = (df['Open'] + df['Close']) / 2.0
    for i in range(1, len(ha)):
        ha.iloc[i, ha.columns.get_loc('HA_Open')] = (ha.iloc[i-1]['HA_Open'] + ha.iloc[i-1]['HA_Close']) / 2.0
    ha['HA_High'] = pd.concat([df['High'], ha['HA_Open'], ha['HA_Close']], axis=1).max(axis=1)
    ha['HA_Low']  = pd.concat([df['Low'],  ha['HA_Open'], ha['HA_Close']], axis=1).min(axis=1)
    return ha

def heikin_ashi_signal(df: pd.DataFrame) -> str:
    if df is None or df.empty: return "n/a"
    ha = _heikin_ashi(df).tail(3)
    if len(ha) < 3: return "n/a"
    rising = ha['HA_Close'].is_monotonic_increasing and (ha['HA_Close'] > ha['HA_Open']).all()
    falling = ha['HA_Close'].is_monotonic_decreasing and (ha['HA_Close'] < ha['HA_Open']).all()
    if rising: return "Uptrend (HA)"
    if falling: return "Downtrend (HA)"
    return "Mixed (HA)"

def fib_extensions(df: pd.DataFrame) -> dict:
    if df is None or df.empty or len(df) < 30: return {}
    close = df['Close'].tail(60)
    lo, hi = close.min(), close.max()
    direction_up = close.iloc[-1] >= (lo + hi) / 2.0
    extent = abs(hi - lo)
    if extent <= 0: return {}
    if direction_up:
        ref = hi
        levels = {
            "1.272": ref + 0.272 * extent,
            "1.414": ref + 0.414 * extent,
            "1.618": ref + 0.618 * extent,
        }
    else:
        ref = lo
        levels = {
            "1.272": ref - 0.272 * extent,
            "1.414": ref - 0.414 * extent,
            "1.618": ref - 0.618 * extent,
        }
    return {k: float(v) for k, v in levels.items()}

def elliott_wave_hint(df: pd.DataFrame) -> str:
    if df is None or df.empty or len(df) < 30: return "n/a"
    close = df['Close'].tail(60)
    up = (close > close.shift(1)).sum()
    down = (close < close.shift(1)).sum()
    if up >= down + 8: return "Impulsive up (EW hint)"
    if down >= up + 8: return "Impulsive down (EW hint)"
    return "Corrective / sideways (EW hint)"

def render_advanced_explain(sym: str) -> None:
    st.markdown("### Advanced: Elliott Wave / Fibonacci Extensions / Heikin Ashi")
    # Mini chart + data fetch
    df = pd.DataFrame()
    try:
        import yfinance as yf
        df = yf.download(sym, period="6mo", interval="1d", progress=False, auto_adjust=False)
    except Exception:
        pass
    if df is None or df.empty:
        st.info("Price history unavailable for advanced explanation.")
        return
    # Small chart (Close)
    st.line_chart(df["Close"].rename(sym))
    # Readouts
    st.write("**Heikin Ashi trend:**", heikin_ashi_signal(df))
    levels = fib_extensions(df)
    if levels:
        st.write("**Fib extensions (approx):**", ", ".join([f"{k}: {v:,.2f}" for k, v in levels.items()]))
    else:
        st.write("**Fib extensions:** n/a")
    st.write("**Elliott Wave hint:**", elliott_wave_hint(df))
