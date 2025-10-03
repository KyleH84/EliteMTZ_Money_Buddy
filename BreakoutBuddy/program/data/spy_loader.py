from __future__ import annotations
import pandas as pd
import yfinance as yf

def get_spy_prices(period: str = "5y", interval: str = "1d") -> pd.DataFrame:
    spy = yf.Ticker("SPY")
    df = spy.history(period=period, interval=interval).reset_index()
    df.rename(columns={"Date":"Date","Close":"Close"}, inplace=True)
    return df[["Date","Close"]]
