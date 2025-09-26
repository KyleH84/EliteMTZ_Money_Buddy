from __future__ import annotations
import datetime as dt
from dataclasses import dataclass
from typing import Iterable, List
import math
import pandas as pd

@dataclass
class SnapRow:
    Ticker: str
    Open: float | None = None
    High: float | None = None
    Low: float | None = None
    Close: float | None = None
    PrevClose: float | None = None
    Volume: float | None = None
    AvgVol20: float | None = None
    RVOL: float | None = None
    Change: float | None = None
    ChangePct: float | None = None
    High52w: float | None = None
    Low52w: float | None = None
    DataStatus: str = "EMPTY"

def _safe_float(x):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        return float(x)
    except Exception:
        return None

def get_ohlcv_for_tickers(tickers: Iterable[str]) -> pd.DataFrame:
    # Return a DataFrame with OHLC, PrevClose, Volume, AvgVol20, RVOL, Change, ChangePct, 52w stats for each ticker.
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        return pd.DataFrame([SnapRow(Ticker=str(t).upper(), DataStatus="IMPORT_ERROR").__dict__ for t in tickers])

    out: List[dict] = []

    for t in list(dict.fromkeys([str(x).strip().upper() for x in tickers if str(x).strip()])):
        row = SnapRow(Ticker=t)
        try:
            tk = yf.Ticker(t)
            hist = tk.history(period="60d", interval="1d", auto_adjust=False, prepost=False)
            if hist is not None and not getattr(hist, "empty", True):
                last = hist.tail(1).iloc[0]
                row.Open = _safe_float(last.get("Open"))
                row.High = _safe_float(last.get("High"))
                row.Low = _safe_float(last.get("Low"))
                row.Close = _safe_float(last.get("Close"))
                if len(hist) >= 2:
                    prev = hist.tail(2).iloc[0]
                    row.PrevClose = _safe_float(prev.get("Close"))
                row.Volume = _safe_float(last.get("Volume"))
                if len(hist) >= 20:
                    row.AvgVol20 = float(hist["Volume"].tail(20).mean())
                elif len(hist) > 0:
                    row.AvgVol20 = float(hist["Volume"].mean())
                if row.Volume and row.AvgVol20 and row.AvgVol20 > 0:
                    row.RVOL = row.Volume / row.AvgVol20
                if row.Close is not None and row.PrevClose not in (None, 0):
                    row.Change = row.Close - row.PrevClose
                    row.ChangePct = (row.Change / row.PrevClose) * 100.0

            try:
                fi = getattr(tk, "fast_info", None)
                if fi:
                    row.High52w = _safe_float(getattr(fi, "year_high", None))
                    row.Low52w = _safe_float(getattr(fi, "year_low", None))
            except Exception:
                pass

            row.DataStatus = "OK" if row.Close is not None else "EMPTY"
        except Exception:
            row.DataStatus = "ERROR"

        out.append(row.__dict__)

    df = pd.DataFrame(out)
    for c in ["Open","High","Low","Close","PrevClose","Change"]:
        if c in df.columns:
            df[c] = df[c].astype(float).round(2)
    for c in ["ChangePct","RVOL"]:
        if c in df.columns:
            df[c] = df[c].astype(float).round(2)
    return df