# BreakoutBuddy/program/utilities/feature_fixups.py
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
        if pd.isna(delta.iloc[i]) or pd.isna(delta.iloc[i-1]): streak.iloc[i]=0
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

    return df

# === ConnorsRSI computation helpers ===
import numpy as np
import pandas as pd

def _rsi(series: pd.Series, length: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(length, min_periods=length).mean()
    loss = (-delta.clip(upper=0)).rolling(length, min_periods=length).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _streak(series: pd.Series) -> pd.Series:
    delta = series.diff()
    sign = np.sign(delta).replace(0, np.nan)
    streak = pd.Series(0.0, index=series.index)
    run = 0.0
    last = np.nan
    for i, s in enumerate(sign):
        if np.isnan(s):
            run = 0.0
        elif s == last:
            run += s
        else:
            run = s
        streak.iloc[i] = run
        last = s
    return streak

def _percent_rank(series: pd.Series, length: int) -> pd.Series:
    def pr(x):
        s = pd.Series(x)
        return 100.0 * s.rank(pct=True).iloc[-1]
    return series.rolling(length, min_periods=length).apply(pr, raw=False)

def compute_connorsrsi(close: pd.Series,
                       rsi_len: int = 3,
                       streak_rsi_len: int = 2,
                       pr_len: int = 100) -> pd.Series:
    rsi_price = _rsi(close, rsi_len)
    streak = _streak(close)
    rsi_streak = _rsi(streak.fillna(0), streak_rsi_len)
    chg2 = close.diff(2)
    pr = _percent_rank(chg2, pr_len)
    crsi = (rsi_price + rsi_streak + pr) / 3.0
    return crsi.rename("ConnorsRSI")

def ensure_connorsrsi(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    price_col = None
    for c in ["close","Close","adj_close","Adj Close","price","Price"]:
        if c in out.columns:
            price_col = c; break
    if price_col is not None:
        if "ConnorsRSI" not in out.columns:
            out["ConnorsRSI"] = compute_connorsrsi(pd.to_numeric(out[price_col], errors="coerce"))
    else:
        if "ConnorsRSI" not in out.columns:
            out["ConnorsRSI"] = np.nan
    return out


def ensure_basic_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = ensure_connorsrsi(df)
    # P_up: derive from ConnorsRSI as a simple proxy if missing
    if "P_up" not in out.columns:
        if "ConnorsRSI" in out.columns:
            pu = (out["ConnorsRSI"] / 100.0).clip(0,1)
            out["P_up"] = pu.rolling(3, min_periods=1).mean()
        else:
            out["P_up"] = 0.5
    # SqueezeHint from BB width percentile
    price_col = None
    for c in ["close","Close","adj_close","Adj Close","price","Price"]:
        if c in out.columns:
            price_col = c; break
    if "SqueezeHint" not in out.columns and price_col:
        s = pd.to_numeric(out[price_col], errors="coerce")
        try:
            bb_mid = s.rolling(20, min_periods=20).mean()
            bb_std = s.rolling(20, min_periods=20).std()
            bb_up = bb_mid + 2*bb_std
            bb_dn = bb_mid - 2*bb_std
            width = (bb_up - bb_dn) / (bb_mid.replace(0, np.nan)).abs()
            pct = width.rank(pct=True)
            out["SqueezeHint"] = 1.0 - pct
        except Exception:
            out["SqueezeHint"] = np.nan
    elif "SqueezeHint" not in out.columns:
        out["SqueezeHint"] = np.nan
    return out


def report_feature_gaps(df):
    """
    Return a small audit table with counts of missing or non-finite values for key features.
    """
    import numpy as np, pandas as pd
    cols = ["ConnorsRSI", "P_up", "SqueezeHint", "RelSPY"]
    rep = []
    for c in cols:
        if c in df.columns:
            series = pd.to_numeric(df[c], errors="coerce")
            rep.append({
                "feature": c,
                "missing": int(series.isna().sum()),
                "nonfinite": int(np.isinf(series).sum())
            })
        else:
            rep.append({"feature": c, "missing": None, "nonfinite": None})
    return pd.DataFrame(rep)
