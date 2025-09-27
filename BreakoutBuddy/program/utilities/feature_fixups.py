# utilities/feature_fixups.py
import numpy as np, pandas as pd

def _to_numeric(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
    return df

def compute_rsi(series: pd.Series, period: int = 14):
    s = pd.to_numeric(series, errors='coerce')
    d = s.diff(); up = d.clip(lower=0.0); dn = -d.clip(upper=0.0)
    r_up = up.ewm(alpha=1/period, adjust=False).mean()
    r_dn = dn.ewm(alpha=1/period, adjust=False).mean().replace(0, np.nan)
    rs = r_up / r_dn
    return 100 - (100/(1+rs))

def compute_connors_rsi(close: pd.Series, pr_rsi=3, pr_streak=2, pr_rank=100):
    rsi = compute_rsi(close, pr_rsi)
    delta = close.diff()
    streak = delta.copy()*0.0
    for i in range(1, len(close)):
        if np.isnan(delta.iloc[i]) or np.isnan(delta.iloc[i-1]): streak.iloc[i]=0
        elif delta.iloc[i] > 0:  streak.iloc[i] = streak.iloc[i-1]+1 if streak.iloc[i-1]>0 else 1
        elif delta.iloc[i] < 0:  streak.iloc[i] = streak.iloc[i-1]-1 if streak.iloc[i-1]<0 else -1
        else: streak.iloc[i]=0
    streak_rsi = compute_rsi(streak, pr_streak)
    change = delta / close.shift(1) * 100.0
    pct_rank = change.rolling(pr_rank).apply(lambda x: (pd.Series(x).rank(pct=True).iloc[-1]*100), raw=False)
    return (rsi + streak_rsi + pct_rank)/3.0

def compute_rvol(volume: pd.Series, window=20):
    v = pd.to_numeric(volume, errors='coerce')
    ma = v.rolling(window).mean()
    return v/ma

def compute_relspy(stock_close: pd.Series, spy_close: pd.Series, lookback=20):
    sc = pd.to_numeric(stock_close, errors='coerce')
    sp = pd.to_numeric(spy_close.reindex(sc.index), errors='coerce')
    s_ret = sc / sc.shift(lookback)
    sp_ret = sp / sp.shift(lookback)
    return s_ret / sp_ret

def compute_squeeze_hint(close, high, low, window=20, mult_bb=2.0, mult_kc=1.5):
    c = pd.to_numeric(close, errors='coerce')
    h = pd.to_numeric(high, errors='coerce')
    l = pd.to_numeric(low, errors='coerce')
    mid = c.rolling(window).mean(); std = c.rolling(window).std()
    bbw = (mid + mult_bb*std) - (mid - mult_bb*std)
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(window).mean(); kcw = 2*mult_kc*atr
    return (bbw < kcw).astype(float)

def fill_feature_gaps(df: pd.DataFrame, spy_ref=None,
                      price_cols=('Close','High','Low'), vol_col='Volume'):
    df = df.copy()
    need = [c for c in [*price_cols, vol_col] if c in df.columns]
    df = _to_numeric(df, need)

    close = df.get(price_cols[0]); high = df.get(price_cols[1]); low = df.get(price_cols[2]); vol = df.get(vol_col)

    if 'RSI4' not in df or df['RSI4'].isna().all():
        if close is not None: df['RSI4'] = compute_rsi(close, 4)
    if 'ConnorsRSI' not in df or df['ConnorsRSI'].isna().all():
        if close is not None: df['ConnorsRSI'] = compute_connors_rsi(close)
    if 'RVOL' not in df or df['RVOL'].isna().all():
        if vol is not None: df['RVOL'] = compute_rvol(vol, 20)
    if 'RelSPY' not in df or df['RelSPY'].isna().all():
        if spy_ref is not None and 'Close' in spy_ref and close is not None:
            df['RelSPY'] = compute_relspy(close, spy_ref['Close'], 20)
    if 'SqueezeHint' not in df or df['SqueezeHint'].isna().all():
        if close is not None and high is not None and low is not None:
            df['SqueezeHint'] = compute_squeeze_hint(close, high, low)

    # P_up baseline only if fully missing
    if 'P_up' not in df or df['P_up'].isna().all():
        rsi = df.get('RSI4'); rel = df.get('RelSPY')
        if rsi is not None and rel is not None:
            rsi_z = (rsi - 50)/50.0
            rel_z = rel - 1.0
            score = 0.6*rsi_z + 0.4*rel_z
            df['P_up'] = 1/(1+np.exp(-score))

    for c in ['RelSPY','RVOL','RSI4','ConnorsRSI','SqueezeHint','P_up']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')

    return df

def report_feature_gaps(df: pd.DataFrame, cols=None):
    if cols is None: cols = ['P_up','RelSPY','RVOL','RSI4','ConnorsRSI','SqueezeHint']
    out = []
    for c in cols:
        if c in df.columns: out.append((c, int(df[c].isna().sum())))
        else: out.append((c, 'missing'))
    return pd.DataFrame(out, columns=['column','null_count'])