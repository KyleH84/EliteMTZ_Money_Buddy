import datetime as _dt
from typing import Tuple
import pandas as pd
import yfinance as yf

def _tf_map(tf: str) -> Tuple[dict, str]:
    """Return kwargs for yf.Ticker().history and a human label."""
    tf = (tf or "6M").upper()
    if tf == "1D":
        return ({"period":"1d", "interval":"5m"}, "1 day, 5‑min bars")
    if tf == "5D":
        return ({"period":"5d", "interval":"5m"}, "5 days, 5‑min bars")
    if tf == "1M":
        return ({"period":"1mo", "interval":"30m"}, "1 month, 30‑min bars")
    if tf == "3M":
        return ({"period":"3mo", "interval":"1d"}, "3 months, daily")
    if tf == "6M":
        return ({"period":"6mo", "interval":"1d"}, "6 months, daily")
    if tf == "1Y":
        return ({"period":"1y", "interval":"1d"}, "1 year, daily")
    if tf == "2Y":
        return ({"period":"2y", "interval":"1d"}, "2 years, daily")
    if tf == "5Y":
        return ({"period":"5y", "interval":"1wk"}, "5 years, weekly")
    if tf == "10Y":
        return ({"period":"10y", "interval":"1wk"}, "10 years, weekly")
    if tf == "YTD":
        start = _dt.date(_dt.date.today().year, 1, 1)
        return ({"start": start, "interval":"1d"}, "Year‑to‑date, daily")
    # Default
    if tf == "MAX":
        return ({"period":"max", "interval":"1mo"}, "Max, monthly")
    return ({"period":"6mo", "interval":"1d"}, "6 months, daily")

def fetch_history(symbol: str, timeframe: str) -> pd.DataFrame:
    """Fetch OHLCV for symbol at a timeframe, with sensible fallbacks."""
    t = yf.Ticker(symbol)
    kwargs, _ = _tf_map(timeframe)
    try:
        df = t.history(**kwargs)
    except Exception:
        # Fallback to coarser interval
        fallback = {"period":"6mo", "interval":"1d"}
        df = t.history(**fallback)
    if df is None:
        return pd.DataFrame()
    if df.empty:
        return df
    # Normalize multiindex columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    # Standardize column names
    for c in ["Open","High","Low","Close","Volume"]:
        if c not in df.columns and c.title() in df.columns:
            df[c] = df[c.title()]
    return df

def build_chart(symbol: str, timeframe: str = "6M", style: str = "Candles"):
    """Return a Plotly figure for the symbol/timeframe."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    df = fetch_history(symbol, timeframe)
    if df is None or df.empty:
        return go.Figure()

    if style.lower().startswith("line"):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Close"))
        if "Volume" in df.columns:
            # Show volume on secondary axis area style
            vol = df["Volume"].fillna(0)
            fig.add_trace(go.Bar(x=df.index, y=vol, name="Volume", opacity=0.3, yaxis="y2"))
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, rangemode="tozero"))
    else:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.75, 0.25], vertical_spacing=0.04)
        fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"],
                                     low=df["Low"], close=df["Close"], name="Price"),
                      row=1, col=1)
        if "Volume" in df.columns:
            fig.add_trace(go.Bar(x=df.index, y=df["Volume"].fillna(0), name="Volume", opacity=0.4),
                          row=2, col=1)
        fig.update_yaxes(rangemode="tozero", row=2, col=1)

    # Layout polish
    fig.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
    )
    return fig


# --- Simple chart wrapper with optional RSI overlays ---
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(gain, index=series.index).rolling(period).mean()
    roll_down = pd.Series(loss, index=series.index).rolling(period).mean()
    rs = roll_up / (roll_down.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(method="bfill").clip(0, 100)

def render_price_chart(ticker: str, timeframe: str = "3M", show_rsi4: bool=False, show_crsi: bool=False):
    if not ticker:
        return
    kwargs, _ = _tf_map(timeframe)
    try:
        df = yf.Ticker(ticker).history(**kwargs)
    except Exception:
        df = None
    if df is None or df.empty:
        return

    rows = 2 + (1 if (show_rsi4 or show_crsi) else 0)
    specs = [[{"secondary_y": False}], [{"secondary_y": False}]] + ([[{"secondary_y": False}]] if rows==3 else [])
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.02, specs=specs)

    # Price (row 1)
    if {"Open","High","Low","Close"}.issubset(df.columns):
        fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="OHLC"),
                      row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Close"), row=1, col=1)

    # Volume (row 2)
    if "Volume" in df.columns:
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"].fillna(0), name="Volume", opacity=0.4), row=2, col=1)
        fig.update_yaxes(rangemode="tozero", row=2, col=1)

    # RSI overlays (row 3)
    if rows == 3:
        try:
            if "Close" in df.columns:
                if show_rsi4:
                    rsi4 = _rsi(df["Close"], period=4)
                    fig.add_trace(go.Scatter(x=df.index, y=rsi4, name="RSI(4)", mode="lines"), row=3, col=1)
                if show_crsi:
                    # Approximate ConnorsRSI as avg of RSI(3), 2-period streak RSI, 100-period percent rank of change
                    rsi3 = _rsi(df["Close"], period=3)
                    # Streak: consecutive up/down days length
                    chg = df["Close"].diff().fillna(0)
                    streak = (chg.groupby((chg * chg.shift(1) < 0).cumsum()).cumcount() + 1) * np.sign(chg)
                    streak_rsi = _rsi(pd.Series(streak, index=df.index).abs(), period=2)
                    # Percent rank of 1-day return over 100
                    look = 100 if len(chg) >= 100 else max(5, len(chg)//2)
                    prk = chg.rolling(look).apply(lambda s: 100.0 * (s.rank(pct=True).iloc[-1]), raw=False)
                    crsi = (rsi3 + streak_rsi + prk.fillna(50)) / 3.0
                    fig.add_trace(go.Scatter(x=df.index, y=crsi, name="ConnorsRSI", mode="lines"), row=3, col=1)
            fig.update_yaxes(range=[0,100], row=3, col=1)
        except Exception:
            pass

    fig.update_layout(height=460 if rows==2 else 620, margin=dict(l=10,r=10,t=10,b=10), showlegend=False,
                      hovermode="x unified", xaxis_rangeslider_visible=False)
    try:
        import streamlit as st
        st.plotly_chart(fig, width="stretch")
    except Exception:
        pass
