
import pandas as pd, numpy as np
def connors_rsi(close: pd.Series, rsi_period=4, streak_period=2, pr_len=20) -> pd.Series:
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / (loss.replace(0, np.nan))
    rsi_short = (100 - (100 / (1 + rs))).clip(0, 100)
    up = (close > close.shift(1)).astype(int)
    streak = up.groupby((up != up.shift()).cumsum()).cumsum()
    rsi_streak = (streak.rolling(streak_period).mean() / streak.rolling(streak_period).max() * 100)
    pr = close.pct_change(pr_len).rank(pct=True) * 100
    return (rsi_short.fillna(50) + rsi_streak.fillna(50) + pr.fillna(50)) / 3
