# Program/utilities/context_weight.py
from __future__ import annotations
from datetime import datetime, timezone
import pandas as pd
import numpy as np

_EPOCH = datetime(2000,1,6,18,14, tzinfo=timezone.utc)  # near new moon
_SYNODIC = 29.530588853  # days

def moon_phase_fraction(dt: datetime) -> float:
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    days = (dt - _EPOCH).total_seconds() / 86400.0
    frac = (days % _SYNODIC) / _SYNODIC
    return float(frac)

def moon_quadrant_from_fraction(frac: float) -> int:
    return int(np.floor((frac * 4.0) % 4))

def moon_quadrant_on(dt: datetime) -> int:
    return moon_quadrant_from_fraction(moon_phase_fraction(dt))

def moon_quadrant_today() -> int:
    return moon_quadrant_on(datetime.now(timezone.utc))

def moon_quadrant_from_series(dates: pd.Series) -> pd.Series:
    return dates.apply(lambda d: moon_quadrant_on(pd.to_datetime(d).to_pydatetime()))
