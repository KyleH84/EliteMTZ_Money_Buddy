from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# utilities/oracle_engine.py
from dataclasses import dataclass
from typing import Dict, Any
import datetime as dt
from utilities.oracle_data import moon_phase_bucket, moon_phase_fraction, kp_index_recent, solar_flare_activity, market_volatility_proxy
from utilities.alignment import planetary_alignment_index
@dataclass
class OracleSettings:
    use_moon: bool = True
    use_markets: bool = True
    use_space: bool = True
    use_weird: bool = True
    user_sign: str = ""
def compute_oracle(today: dt.date, lo: int, hi: int, settings: OracleSettings) -> Dict[str, Any]:
    parts = {"moon": 0.0, "markets": 0.0, "space": 0.0, "weird": 0.0}
    chaos = 0.0
    score_mult: Dict[str, float] = {}
    if settings.use_moon:
        phase = moon_phase_bucket(today)
        if phase == "full":
            parts["moon"] = 0.08; chaos += 0.05
        elif phase == "new":
            parts["moon"] = 0.05; chaos += 0.03
        else:
            parts["moon"] = 0.03; chaos += 0.01
        if phase == "full":
            for n in range(lo, hi+1):
                if n % 9 == 0:
                    score_mult[str(n)] = score_mult.get(str(n),1.0)*1.04
    if settings.use_markets:
        v = market_volatility_proxy()
        if v is not None:
            v_clamped = float(max(10.0, min(40.0, v)))
            parts["markets"] = (v_clamped - 10.0) / 250.0
            chaos += (v_clamped - 10.0) / 500.0
    if settings.use_space:
        kp = kp_index_recent()
        fl = solar_flare_activity()
        kp_part = min(0.12, max(0.0, (float(kp or 0)/9.0)*0.12))
        flare_part = min(0.06, 0.02*float(fl.get("M",0)) + 0.04*float(fl.get("X",0)))
        parts["space"] = kp_part + flare_part
        chaos += min(0.08, float(kp or 0)/9.0*0.08)
    if settings.use_weird:
        ai = planetary_alignment_index(dt.datetime.combine(today, dt.time(12,0))).get("alignment_index", 0.5)
        parts["weird"] = 0.03*float(ai)
        chaos += 0.01*float(ai)
    chaos = float(min(0.30, max(0.0, chaos)))
    return {"score_mult": score_mult, "chaos": chaos, "parts": parts}
