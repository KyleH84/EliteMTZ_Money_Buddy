from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import datetime as dt
from pathlib import Path
from typing import Dict, Any
import pandas as pd
import numpy as np

# soft deps from your oracle modules (fallbacks provided)
try:
    from utilities.oracle_data import kp_index_recent, solar_flare_activity, market_volatility_proxy, moon_phase_bucket, moon_phase_fraction
except Exception:
    def kp_index_recent(): return None
    def solar_flare_activity(): return {"M":0,"X":0}
    def market_volatility_proxy(): return None
    def moon_phase_bucket(d=None): return "n/a"
    def moon_phase_fraction(d=None): return 0.0

try:
    from utilities.planetary_alignment import planetary_features_for_date
except Exception:
    def planetary_features_for_date(date): return {"alignment_index":0.0,"conjunction_rate":0,"mercury_retro":False}

CALENDAR = ["dow","dom","woy","month","is_weekend"]

def _calendar_feats(d: dt.date) -> Dict[str, Any]:
    iso = d.isocalendar()
    return {"dow": d.weekday(), "dom": d.day, "woy": int(iso[1]), "month": d.month, "is_weekend": int(d.weekday()>=5)}

def _oracle_feats(d: dt.date) -> Dict[str, Any]:
    kp = kp_index_recent()
    fl = solar_flare_activity() or {"M":0,"X":0}
    vix = market_volatility_proxy()
    moonf = moon_phase_fraction(d); moonb = moon_phase_bucket(d)
    pf = planetary_features_for_date(d)
    return {
        "lunar_phase": moonf, "lunar_bucket": moonb,
        "kp_3h_or_recent": kp if kp is not None else np.nan,
        "kp_24h_max": np.nan, "ap_daily": np.nan, "f107_flux": np.nan,
        "flare_m72h": fl.get("M",0), "flare_x72h": fl.get("X",0),
        "vix_close_or_spy20d": vix if vix is not None else np.nan,
        "alignment_index": pf.get("alignment_index",0.0),
        "conjunction_rate": pf.get("conjunction_rate",0),
        "mercury_retro": int(bool(pf.get("mercury_retro", False)))
    }

def enrich_csv(path: Path, date_col: str="draw_date") -> Path:
    df = pd.read_csv(path)
    if date_col not in df.columns:
        for alt in ["date","drawDate","DrawDate"]:
            if alt in df.columns: date_col = alt; break
    dates = pd.to_datetime(df[date_col], errors="coerce").dt.date
    rows = []
    for d in dates.fillna(method="ffill").fillna(method="bfill"):
        d = d if isinstance(d, dt.date) else dt.date.today()
        feats = _oracle_feats(d); feats.update(_calendar_feats(d))
        rows.append(feats)
    E = pd.DataFrame(rows)
    out = pd.concat([df, E], axis=1)
    out.to_csv(path, index=False)
    return path

def enrich_all_cached(data_dir: Path = Path("Data")) -> dict:
    res = {}
    for p in data_dir.glob("cached_*_data.csv"):
        try:
            enrich_csv(p); res[p.name]="ok"
        except Exception as e:
            res[p.name]=f"failed: {e}"
    return res
