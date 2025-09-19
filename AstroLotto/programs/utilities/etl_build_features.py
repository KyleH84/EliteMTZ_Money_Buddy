# utilities/etl_build_features.py
from __future__ import annotations
import math, datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from utilities.oracle_data import moon_phase_fraction, moon_phase_bucket, kp_lookup_before, f10_7_flux_lookup, flare_counts_before
from utilities.alignment import planetary_alignment_index, mercury_retrograde_flag

@dataclass
class ETLConfig:
    draws_csv: Path
    out_csv: Path
    game: str
    datetime_col: str = "date"
    date_is_local: bool = False
    ephemeris_dir: Path = Path("Data")

def _seasonality(when: dt.datetime):
    doy = when.timetuple().tm_yday
    ang = 2*np.pi*doy/366.0
    return math.sin(ang), math.cos(ang)

def build_features(cfg: ETLConfig) -> pd.DataFrame:
    df = pd.read_csv(cfg.draws_csv)
    if cfg.datetime_col not in df.columns:
        raise ValueError(f"Missing datetime column {cfg.datetime_col}")
    df["draw_ts"] = pd.to_datetime(df[cfg.datetime_col], utc=True, errors="coerce")
    df = df.dropna(subset=["draw_ts"]).copy()
    df["draw_date"] = df["draw_ts"].dt.date
    feats = []
    for _, row in df.iterrows():
        ts: pd.Timestamp = row["draw_ts"]
        d = ts.date()
        moon_frac = float(moon_phase_fraction(d))
        moon_b = moon_phase_bucket(d)
        kp3h = kp_lookup_before(ts.to_pydatetime())
        fl = flare_counts_before(ts.to_pydatetime(), window_hours=72)
        f107 = f10_7_flux_lookup(d)
        al = planetary_alignment_index(ts.to_pydatetime())
        retro = mercury_retrograde_flag(ts.to_pydatetime())
        siny, cosy = _seasonality(ts.to_pydatetime())
        dow = int(ts.weekday())
        feats.append({
            "draw_ts": ts,
            "lunar_phase_frac": moon_frac,
            "lunar_phase_bucket": moon_b,
            "kp_prev_bin": kp3h if kp3h is not None else np.nan,
            "flare_M_72h": int(fl.get("M",0)),
            "flare_X_72h": int(fl.get("X",0)),
            "f10_7_flux": f107 if f107 is not None else np.nan,
            "alignment_index": float(al.get("alignment_index", 0.5)),
            "conjunction_rate": float(al.get("conjunction_rate", 0.0)),
            "mercury_retro": int(retro),
            "dow": dow,
            "doy_sin": float(siny),
            "doy_cos": float(cosy),
        })
    featdf = pd.DataFrame(feats)
    out = df.merge(featdf, on="draw_ts", how="left")
    cfg.out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(cfg.out_csv, index=False)
    return out
