from __future__ import annotations
import pandas as pd, numpy as np

# ---------- helpers ----------
def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1/period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / roll_down
    return 100.0 - (100.0 / (1.0 + rs))

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df['High'], df['Low'], df['Close']
    prev_c = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def _streak(changes: pd.Series) -> pd.Series:
    s = np.sign(changes.fillna(0.0))
    return (s.groupby((s != s.shift()).cumsum()).cumcount()+1) * s

def _percent_rank(values: pd.Series, window: int = 100) -> pd.Series:
    return values.rolling(window).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100.0, raw=False)

def _connors_rsi(close: pd.Series) -> pd.Series:
    rsi3 = _rsi(close, 3)
    chg = close.diff()
    streak = _streak(chg)
    rsi_streak = _rsi(streak, 2)
    pr_2 = _percent_rank(close.pct_change(2).fillna(0.0), 100)
    return (rsi3 + rsi_streak + pr_2) / 3.0

def _squeeze_hint(df: pd.DataFrame) -> pd.Series:
    close = df['Close']
    mid = close.rolling(20).mean()
    std = close.rolling(20).std(ddof=0)
    bb_up = mid + 2*std
    bb_dn = mid - 2*std
    atr20 = _atr(df, 20)
    k_up = mid + 1.5*atr20
    k_dn = mid - 1.5*atr20
    bb_width = (bb_up - bb_dn)
    k_width = (k_up - k_dn)
    return (bb_width < k_width).map(lambda x: 'Squeeze' if bool(x) else 'Off')

def _p_up(close: pd.Series, lookback:int=20) -> float:
    if len(close) < max(lookback, 2):
        return 50.0
    r = close.pct_change().tail(lookback)
    return float((r > 0).mean() * 100.0)

def _download_prices(tickers: list[str], period: str = '120d'):
    try:
        import yfinance as yf
    except Exception:
        return {}
    if not tickers:
        return {}
    data = yf.download(tickers, period=period, interval='1d', group_by='ticker', auto_adjust=False, threads=True, progress=False)
    out = {}
    if isinstance(data.columns, pd.MultiIndex):
        for t in tickers:
            if t in data.columns.get_level_values(0):
                df = data[t].dropna()
                if {'Open','High','Low','Close','Volume'}.issubset(df.columns):
                    out[t] = df
    else:
        t = tickers[0]
        out[t] = data.dropna()
    return out

# ---------- public API ----------
def _normalize_tickers(frame: pd.DataFrame) -> pd.DataFrame:
    """Safely ensure a 'Ticker' column of uppercase strings; never call .upper() on a Series."""
    f = frame.copy()
    col = None
    if 'Ticker' in f.columns:
        col = 'Ticker'
    elif 'Symbol' in f.columns:
        f = f.rename(columns={'Symbol':'Ticker'})
        col = 'Ticker'
    else:
        # synthesize a Ticker from index if needed
        f['Ticker'] = f.index.astype(str)
        col = 'Ticker'
    # Use .astype(str) + .str.* to avoid Series attribute errors
    f[col] = f[col].astype(str).str.upper().str.strip()
    return f

def enrich_snapshot(view: pd.DataFrame) -> pd.DataFrame:
    """Dedup tickers and fill indicator columns from yfinance. Avoid blanks where computable."""
    if view is None or len(view) == 0:
        return view

    # Normalize & dedupe by Ticker
    view = _normalize_tickers(view)
    view = view.groupby('Ticker', as_index=False).last()

    # Ensure baseline numeric columns exist
    for c in ['Open','High','Low','Close','Volume']:
        if c not in view.columns:
            view[c] = np.nan

    # Build fetch list (include SPY for RelSPY baseline)
    tickers = sorted(set(view['Ticker'].dropna().astype(str)))
    fetch = tickers if 'SPY' in tickers else tickers + ['SPY']
    prices = _download_prices(fetch)

    spy20 = None
    if 'SPY' in prices and len(prices['SPY']) >= 21:
        spy20 = prices['SPY']['Close'].pct_change(20).iloc[-1]

    for i, row in view.iterrows():
        t = row['Ticker']
        df = prices.get(t)
        if df is None or df.empty:
            # conservative fallbacks
            view.at[i,'P_up'] = float(view.get('P_up', pd.Series(dtype=float)).get(i, 50.0))
            view.at[i,'RelSPY'] = float(view.get('RelSPY', pd.Series(dtype=float)).get(i, 0.0))
            view.at[i,'RVOL'] = float(view.get('RVOL', pd.Series(dtype=float)).get(i, 1.0))
            view.at[i,'RSI4'] = float(view.get('RSI4', pd.Series(dtype=float)).get(i, 0.0))
            view.at[i,'ConnorsRSI'] = float(view.get('ConnorsRSI', pd.Series(dtype=float)).get(i, 0.0))
            view.at[i,'SqueezeHint'] = str(view.get('SqueezeHint', pd.Series(dtype=object)).get(i, 'Off'))
            continue

        # Fill OHLC if missing
        for c in ['Open','High','Low','Close','Volume']:
            if c not in view.columns or pd.isna(row.get(c)):
                view.at[i, c] = float(df[c].iloc[-1])

        # ChangePct (intraday % from open->close)
        try:
            change_pct = (df['Close'].iloc[-1] - df['Open'].iloc[-1]) / df['Open'].iloc[-1] * 100.0
        except Exception:
            change_pct = 0.0
        view.at[i,'ChangePct'] = float(change_pct)

        # P_up (last 20-day % up days)
        view.at[i,'P_up'] = _p_up(df['Close'], 20)

        # RVOL (last vol / 20d avg)
        try:
            view.at[i,'RVOL'] = float(df['Volume'].iloc[-1] / df['Volume'].rolling(20).mean().iloc[-1])
        except Exception:
            view.at[i,'RVOL'] = 1.0

        # RSI4
        try:
            view.at[i,'RSI4'] = float(_rsi(df['Close'], 4).iloc[-1])
        except Exception:
            view.at[i,'RSI4'] = 0.0

        # ConnorsRSI
        try:
            view.at[i,'ConnorsRSI'] = float(_connors_rsi(df['Close']).iloc[-1])
        except Exception:
            view.at[i,'ConnorsRSI'] = 0.0

        # RelSPY (20d)
        try:
            if spy20 is not None and len(df['Close']) >= 21:
                rel = df['Close'].pct_change(20).iloc[-1] - spy20
                view.at[i,'RelSPY'] = float(rel)
            else:
                view.at[i,'RelSPY'] = 0.0
        except Exception:
            view.at[i,'RelSPY'] = 0.0

        # SqueezeHint
        try:
            view.at[i,'SqueezeHint'] = str(_squeeze_hint(df).iloc[-1])
        except Exception:
            view.at[i,'SqueezeHint'] = 'Off'

    # Final NA handling
    for c in ['Open','High','Low','Close','Volume','ChangePct','P_up','RelSPY','RVOL','RSI4','ConnorsRSI']:
        if c in view.columns:
            view[c] = pd.to_numeric(view[c], errors='coerce').fillna(0.0)
    if 'SqueezeHint' in view.columns:
        view['SqueezeHint'] = view['SqueezeHint'].astype(str).replace({'nan':'Off'}).fillna('Off')

    return view
