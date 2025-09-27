# data/spy_loader.py
import pandas as pd
from datetime import datetime, timedelta
from utilities.caching import cache_data

@cache_data(ttl=3600)
def get_spy_prices(period_days: int = 400) -> pd.DataFrame:
    try:
        import yfinance as yf
    except Exception as e:
        raise RuntimeError("yfinance not installed or failed to import") from e
    end = datetime.utcnow()
    start = end - timedelta(days=period_days+10)
    spy = yf.download('SPY', start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), progress=False)
    spy = spy.rename(columns={'Adj Close':'Close'})
    spy = spy[['Close']].dropna()
    spy.index.name = 'Date'
    return spy