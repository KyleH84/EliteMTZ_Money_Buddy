from __future__ import annotations
import pandas as pd, numpy as np

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1/period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / roll_down
    return 100.0 - (100.0 / (1.0 + rs))

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

def safe_fill_indicators(view: pd.DataFrame) -> pd.DataFrame:
    if view is None or len(view) == 0:
        return view
    f = view.copy()
    ticker_col = 'Ticker' if 'Ticker' in f.columns else ('Symbol' if 'Symbol' in f.columns else None)
    if ticker_col is None:
        return view
    syms = f[ticker_col].astype(str).str.upper().str.strip().tolist()
    try:
        import yfinance as yf
        data = yf.download(syms, period='6mo', interval='1d', group_by='ticker', auto_adjust=False, threads=True, progress=False)
    except Exception:
        return view

    def fetch_df(sym: str):
        nonlocal data
        import pandas as pd
        if isinstance(data.columns, pd.MultiIndex):
            if sym in data.columns.get_level_values(0):
                df = data[sym].dropna()
            else:
                return None
        else:
            df = data.dropna()
        if not {'Open','High','Low','Close','Volume'}.issubset(df.columns):
            return None
        return df

    need_rsi4 = 'RSI4' in f.columns
    need_connors = 'ConnorsRSI' in f.columns
    need_relspy = 'RelSPY' in f.columns
    need_rvol = 'RVOL' in f.columns
    need_pup = 'P_up' in f.columns
    need_squeeze = 'SqueezeHint' in f.columns

    spy20 = None
    if need_relspy:
        spy = fetch_df('SPY')
        if spy is not None and len(spy) >= 21:
            spy20 = spy['Close'].pct_change(20).iloc[-1]

    for i, row in f.iterrows():
        sym = str(row[ticker_col]).upper().strip()
        df = fetch_df(sym)
        if df is None or df.empty:
            continue

        if need_pup and (pd.isna(row.get('P_up')) or str(row.get('P_up')).lower() in ('none','')):
            r = df['Close'].pct_change().tail(20)
            f.at[i,'P_up'] = float((r > 0).mean() * 100.0)

        if need_rvol and (pd.isna(row.get('RVOL')) or str(row.get('RVOL')).lower() in ('none','')):
            try:
                f.at[i,'RVOL'] = float(df['Volume'].iloc[-1] / df['Volume'].rolling(20).mean().iloc[-1])
            except Exception:
                pass

        if need_rsi4 and (pd.isna(row.get('RSI4')) or str(row.get('RSI4')).lower() in ('none','')):
            try:
                f.at[i,'RSI4'] = float(_rsi(df['Close'], 4).iloc[-1])
            except Exception:
                pass

        if need_connors and (pd.isna(row.get('ConnorsRSI')) or str(row.get('ConnorsRSI')).lower() in ('none','')):
            try:
                rsi3 = _rsi(df['Close'], 3)
                chg = df['Close'].diff()
                s = _streak(chg)
                rsi_streak = _rsi(s, 2)
                pr_2 = df['Close'].pct_change(2).rolling(100).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100.0, raw=False)
                f.at[i,'ConnorsRSI'] = float((rsi3.iloc[-1] + rsi_streak.iloc[-1] + pr_2.iloc[-1]) / 3.0)
            except Exception:
                pass

        if need_relspy and spy20 is not None and (pd.isna(row.get('RelSPY')) or str(row.get('RelSPY')).lower() in ('none','')):
            try:
                f.at[i,'RelSPY'] = float(df['Close'].pct_change(20).iloc[-1] - spy20)
            except Exception:
                pass

        if need_squeeze and (pd.isna(row.get('SqueezeHint')) or str(row.get('SqueezeHint')).lower() in ('none','')):
            try:
                mid = df['Close'].rolling(20).mean()
                std = df['Close'].rolling(20).std(ddof=0)
                bb_up = mid + 2*std
                bb_dn = mid - 2*std
                prev = df['Close'].shift(1)
                tr = pd.concat([(df['High']-df['Low']).abs(), (df['High']-prev).abs(), (df['Low']-prev).abs()], axis=1).max(axis=1)
                atr20 = tr.ewm(alpha=1/20, adjust=False).mean()
                k_up = mid + 1.5*atr20
                k_dn = mid - 1.5*atr20
                f.at[i,'SqueezeHint'] = 'Squeeze' if (bb_up.iloc[-1]-bb_dn.iloc[-1]) < (k_up.iloc[-1]-k_dn.iloc[-1]) else 'Off'
            except Exception:
                pass

    return f
