# Lightweight live indicator fill (no supabase)
from __future__ import annotations
import pandas as pd, numpy as np

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1/period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / roll_down
    return 100 - (100 / (1 + rs))

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df['High'], df['Low'], df['Close']
    prev_close = close.shift(1)
    tr = pd.concat([(high-low).abs(), (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def _streak(changes: pd.Series) -> pd.Series:
    # Positive/negative run length
    sign = np.sign(changes.fillna(0))
    run = (sign.groupby((sign != sign.shift()).cumsum()).cumcount()+1) * sign
    return run

def _percent_rank(values: pd.Series, window: int = 100) -> pd.Series:
    return values.rolling(window).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1]*100, raw=False)

def _connors_rsi(close: pd.Series) -> pd.Series:
    # Simplified CRSI: average of RSI(3), RSI of streak length (2), PercentRank of 2-day change
    rsi3 = _rsi(close, 3)
    chg = close.diff()
    streak = _streak(chg)
    rsi_streak = _rsi(streak, 2)
    pr_2 = _percent_rank(close.pct_change(2).fillna(0), 100)
    return (rsi3 + rsi_streak + pr_2) / 3.0

def _squeeze_hint(df: pd.DataFrame) -> pd.Series:
    # BB(20,2) vs Keltner(20,1.5)
    close = df['Close']
    mid = close.rolling(20).mean()
    std = close.rolling(20).std(ddof=0)
    bb_up = mid + 2*std
    bb_dn = mid - 2*std
    atr = _atr(df, 20)
    k_mid = mid
    k_up = k_mid + 1.5*atr
    k_dn = k_mid - 1.5*atr
    bb_width = (bb_up - bb_dn)
    k_width = (k_up - k_dn)
    return (bb_width < k_width).map(lambda x: 'Squeeze' if x else 'None')

def _download_prices(tickers: list[str], period: str = '90d') -> dict[str, pd.DataFrame]:
    try:
        import yfinance as yf
    except Exception:
        return {}
    data = yf.download(tickers, period=period, interval='1d', group_by='ticker', auto_adjust=False, threads=True, progress=False)
    out = {}
    if isinstance(data.columns, pd.MultiIndex):
        for t in tickers:
            if t in data.columns.get_level_values(0):
                df = data[t].dropna()
                out[t] = df
    else:
        out[tickers[0]] = data.dropna()
    return out

def fill_missing_indicators(view: pd.DataFrame) -> pd.DataFrame:
    if view is None or view.empty: 
        return view
    needed = ['RSI4','ConnorsRSI','RelSPY','RVOL','SqueezeHint']
    need_any = any(col not in view.columns or view[col].isna().any() for col in needed)
    if not need_any:
        return view

    tickers = sorted(set(view['Ticker'].astype(str)))
    # Also fetch SPY for RelSPY baseline
    if 'SPY' not in tickers:
        tickers_plus = tickers + ['SPY']
    else:
        tickers_plus = tickers
    prices = _download_prices(tickers_plus)

    # Compute baseline SPY 20d return
    spy20 = None
    if 'SPY' in prices and len(prices['SPY']) >= 21:
        spy20 = prices['SPY']['Close'].pct_change(20).iloc[-1]

    for i, row in view.iterrows():
        t = str(row['Ticker'])
        df = prices.get(t)
        if df is None or df.empty:
            continue
        # RVOL
        if 'RVOL' not in view.columns or pd.isna(row.get('RVOL')):
            if 'Volume' in df and len(df['Volume']) >= 20:
                view.at[i, 'RVOL'] = float(df['Volume'].iloc[-1] / df['Volume'].rolling(20).mean().iloc[-1])
        # RSI4
        if 'RSI4' not in view.columns or pd.isna(row.get('RSI4')):
            rsi4 = _rsi(df['Close'], 4).iloc[-1]
            view.at[i, 'RSI4'] = float(rsi4)
        # ConnorsRSI
        if 'ConnorsRSI' not in view.columns or pd.isna(row.get('ConnorsRSI')):
            crsi = _connors_rsi(df['Close']).iloc[-1]
            view.at[i, 'ConnorsRSI'] = float(crsi)
        # RelSPY (20d relative performance)
        if 'RelSPY' not in view.columns or pd.isna(row.get('RelSPY')):
            if len(df['Close']) >= 21 and spy20 is not None:
                rel = df['Close'].pct_change(20).iloc[-1] - spy20
                view.at[i, 'RelSPY'] = float(rel)
        # SqueezeHint
        if 'SqueezeHint' not in view.columns or pd.isna(row.get('SqueezeHint')) or str(row.get('SqueezeHint')).lower() == 'none':
            sq = _squeeze_hint(df).iloc[-1]
            view.at[i, 'SqueezeHint'] = str(sq)

    return view
