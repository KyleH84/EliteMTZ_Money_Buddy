from __future__ import annotations
import streamlit as st
import pandas as pd, numpy as np

def _heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    ha = pd.DataFrame(index=df.index)
    ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha['HA_Open'] = ha['HA_Close'].copy()
    ha['HA_Open'].iloc[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha['HA_Open'].iloc[i] = (ha['HA_Open'].iloc[i-1] + ha['HA_Close'].iloc[i-1]) / 2
    ha['HA_High'] = pd.concat([df['High'], ha['HA_Open'], ha['HA_Close']], axis=1).max(axis=1)
    ha['HA_Low']  = pd.concat([df['Low'], ha['HA_Open'], ha['HA_Close']], axis=1).min(axis=1)
    return ha

def heikin_ashi_signal(df: pd.DataFrame) -> str:
    if df is None or df.empty: return "n/a"
    ha = _heikin_ashi(df)
    last = ha[['HA_Open','HA_Close']].tail(3)
    # simple trend cue: last 3 HA closes rising & above HA opens
    if (last['HA_Close'] > last['HA_Open']).all() and last['HA_Close'].is_monotonic_increasing:
        return "Uptrend (HA)"
    if (last['HA_Close'] < last['HA_Open']).all() and last['HA_Close'].is_monotonic_decreasing:
        return "Downtrend (HA)"
    return "Mixed (HA)"

def fib_extensions(df: pd.DataFrame) -> dict:
    # Use last swing high/low window and compute common extension levels
    if df is None or len(df) < 30: return {}
    close = df['Close']
    recent = close.tail(60)
    swing_low  = recent.min()
    swing_high = recent.max()
    # Assume current move is from swing_low -> high if price near high; else high -> low
    direction_up = recent.iloc[-1] > (swing_low + swing_high)/2
    if direction_up:
        base = swing_low; ref = swing_high
        extent = ref - base
        levels = {
            "1.272": ref + 0.272 * extent,
            "1.414": ref + 0.414 * extent,
            "1.618": ref + 0.618 * extent,
        }
    else:
        base = swing_high; ref = swing_low
        extent = base - ref
        levels = {
            "1.272": ref - 0.272 * extent,
            "1.414": ref - 0.414 * extent,
            "1.618": ref - 0.618 * extent,
        }
    return {k: float(v) for k,v in levels.items()}

def elliott_wave_hint(df: pd.DataFrame) -> str:
    # Placeholder heuristic: count recent higher-highs/lows to hint if impulsive/corrective
    if df is None or len(df) < 20: return "n/a"
    close = df['Close'].tail(40)
    hh = (close > close.shift(1)).sum()
    ll = (close < close.shift(1)).sum()
    if hh > ll + 5: return "Impulsive up (EW hint)"
    if ll > hh + 5: return "Impulsive down (EW hint)"
    return "Corrective / sideways (EW hint)"

def render_advanced_explain(sym: str) -> None:
    try:
        import yfinance as yf
        data = yf.download(sym, period="6mo", interval="1d", progress=False, auto_adjust=False)
    except Exception:
        data = pd.DataFrame()
    st.markdown("### Advanced: Elliott Wave / Fibonacci Extensions / Heikin Ashi")
    if data is None or data.empty:
        st.info("Price history unavailable for advanced explanation.")
        return
    # Heikin Ashi trend
    st.write("**Heikin Ashi trend:**", heikin_ashi_signal(data))
    # Fibonacci extensions
    levels = fib_extensions(data)
    if levels:
        st.write("**Fib extensions (approx):**", ", ".join([f"{k}: {v:,.2f}" for k,v in levels.items()]))
    else:
        st.write("**Fib extensions:** n/a")
    # Elliott Wave hint
    st.write("**Elliott Wave hint:**", elliott_wave_hint(data))
