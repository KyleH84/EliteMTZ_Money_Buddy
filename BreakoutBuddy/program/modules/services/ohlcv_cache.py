
from __future__ import annotations
from pathlib import Path
import pandas as pd
import time
import yfinance as yf


from pathlib import Path as _P

def _resolve_data_dir_cache():
    here = _P(__file__).resolve()
    candidates = [
        here.parents[3] / "Data",          # BreakoutBuddy/Data  (repo-level)
        here.parents[2] / "Data",          # BreakoutBuddy/program/Data
        _P.cwd() / "Data",
    ]
    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:
            pass
    return candidates[0]

DATA_DIR = _resolve_data_dir_cache()
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

CACHE_DIR = DATA_DIR / "cache" / "yf"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _cache_file(symbol: str, period: str, interval: str) -> Path:
    safe = symbol.replace("/", "_").upper()
    return CACHE_DIR / f"{safe}_{period}_{interval}.csv"

def get_history(symbol: str, period: str = "1y", interval: str = "1d", ttl_hours: int = 12, retries: int = 2) -> pd.DataFrame:
    fp = _cache_file(symbol, period, interval)
    now = time.time()
    if fp.exists():
        age_h = (now - fp.stat().st_mtime) / 3600.0
        try:
            if age_h <= ttl_hours:
                df = pd.read_csv(fp)
                if not df.empty:
                    return df
        except Exception:
            pass
    last_err = None
    for _ in range(max(1, retries)):
        try:
            df = yf.Ticker(symbol).history(period=period, interval=interval)
            if df is not None and not df.empty:
                out = df.reset_index().rename(columns={"index":"Date"})
                out.to_csv(fp, index=False)
                return out
        except Exception as e:
            last_err = e
            time.sleep(0.8)
    if fp.exists():
        try:
            df = pd.read_csv(fp)
            if not df.empty:
                return df
        except Exception:
            pass
    return pd.DataFrame()
