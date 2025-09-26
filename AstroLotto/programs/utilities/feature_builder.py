from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/feature_builder.py
from pathlib import Path
from typing import Tuple, List, Dict
import numpy as np, pandas as pd
from .features_numeric import rules_for_game, _date_col, last_seen_gap, rolling_freq
from .features_cosmic import zodiac_ordinal, moon_phase_frac, moon_quadrant, mercury_retrograde_flag
from .weather_source import daily_weather_for_game

def _white_cols(df: pd.DataFrame, game: str) -> List[str]:
    prefers = ["white1","white2","white3","white4","white5","white6","n1","n2","n3","n4","n5","n6","ball1","ball2","ball3","ball4","ball5","ball6"]
    cols = [c for c in prefers if c in df.columns]
    k,_wmin,_wmax,_smin,_smax = rules_for_game(game)
    return cols[:k]

def _special_col(df: pd.DataFrame) -> str|None:
    for c in ["powerball","power","pb","mega","megaball","bonus","special"]:
        if c in df.columns: return c
    return None

def build_training_frame(game: str, df_history: pd.DataFrame, extras_dir: Path, program_dir: Path) -> pd.DataFrame:
    # Long-format: one row per candidate number with label 0/1
    k,wmin,wmax,smin,smax = rules_for_game(game)
    dc = _date_col(df_history)
    if dc is None or df_history.empty:
        return pd.DataFrame()
    whites = _white_cols(df_history, game)
    special = _special_col(df_history)
    gaps = last_seen_gap(df_history, dc, whites)
    rf10 = rolling_freq(df_history, whites, 10, wmin, wmax)
    rf30 = rolling_freq(df_history, whites, 30, wmin, wmax)
    rf90 = rolling_freq(df_history, whites, 90, wmin, wmax)

    rows=[]
    for _, row in df_history.iterrows():
        d = pd.to_datetime(row[dc]).date()
        z = zodiac_ordinal(d)
        mp = moon_phase_frac(d)
        mq = moon_quadrant(d)
        mr = mercury_retrograde_flag(d, extras_dir, program_dir)
        wx = daily_weather_for_game(game, d) or {}
        # whites
        appeared = set()
        for c in whites:
            try: appeared.add(int(row[c]))
            except Exception: pass
        for n in range(wmin, wmax+1):
            rows.append({
                "game": game, "draw_date": d, "candidate_number": n,
                "label_drawn": 1 if n in appeared else 0,
                "dow": d.weekday(), "weekofyear": pd.Timestamp(d).isocalendar().week, "month": d.month,
                "era": 0,
                "gap_since_seen": gaps.get(n, 9999),
                "freq10": rf10.get(n,0.0), "freq30": rf30.get(n,0.0), "freq90": rf90.get(n,0.0),
                "parity": n%2, "hi_lo_bin": int(n > (wmin+wmax)//2), "mod3": n%3,
                "zodiac": z, "moon_phase": mp, "moon_quad": mq, "retrograde": mr,
                "wx_temp_mean": wx.get("t_mean"), "wx_temp_max": wx.get("t_max"),
                "wx_precip": 1 if wx.get("precip",0)>0 else 0, "wx_wind": wx.get("w_mean"),
                "head": "white"
            })
        # special
        if smin is not None and special is not None:
            sp = None
            try: sp = int(row[special])
            except Exception: sp=None
            for n in range(smin, smax+1):
                rows.append({
                    "game": game, "draw_date": d, "candidate_number": n,
                    "label_drawn": 1 if sp==n else 0,
                    "dow": d.weekday(), "weekofyear": pd.Timestamp(d).isocalendar().week, "month": d.month,
                    "era": 0,
                    "gap_since_seen": 0, "freq10":0.0, "freq30":0.0, "freq90":0.0,
                    "parity": n%2, "hi_lo_bin": int(n > (smin+smax)//2), "mod3": n%3,
                    "zodiac": z, "moon_phase": mp, "moon_quad": mq, "retrograde": mr,
                    "wx_temp_mean": wx.get("t_mean"), "wx_temp_max": wx.get("t_max"),
                    "wx_precip": 1 if wx.get("precip",0)>0 else 0, "wx_wind": wx.get("w_mean"),
                    "head": "special"
                })
    return pd.DataFrame(rows)

def build_inference_frame(game: str, draw_date, extras_dir: Path, program_dir: Path) -> pd.DataFrame:
    from .draw_schedule import next_draw_date
    k,wmin,wmax,smin,smax = rules_for_game(game)
    d = pd.to_datetime(draw_date).date() if draw_date else next_draw_date(game)
    z = zodiac_ordinal(d); mp = moon_phase_frac(d); mq = moon_quadrant(d); mr = mercury_retrograde_flag(d, extras_dir, program_dir)
    wx = daily_weather_for_game(game, d) or {}
    rows=[]
    for n in range(wmin, wmax+1):
        rows.append({"game":game,"draw_date":d,"candidate_number":n,"dow":d.weekday(),"weekofyear":pd.Timestamp(d).isocalendar().week,
                     "month":d.month,"era":0,"gap_since_seen":0,"freq10":0.0,"freq30":0.0,"freq90":0.0,
                     "parity":n%2,"hi_lo_bin":int(n>(wmin+wmax)//2),"mod3":n%3,
                     "zodiac":z,"moon_phase":mp,"moon_quad":mq,"retrograde":mr,
                     "wx_temp_mean":wx.get("t_mean"),"wx_temp_max":wx.get("t_max"),
                     "wx_precip":1 if wx.get("precip",0)>0 else 0,"wx_wind":wx.get("w_mean"),
                     "head":"white"})
    if smin is not None:
        for n in range(smin, smax+1):
            rows.append({"game":game,"draw_date":d,"candidate_number":n,"dow":d.weekday(),"weekofyear":pd.Timestamp(d).isocalendar().week,
                     "month":d.month,"era":0,"gap_since_seen":0,"freq10":0.0,"freq30":0.0,"freq90":0.0,
                     "parity":n%2,"hi_lo_bin":int(n>(smin+smax)//2),"mod3":n%3,
                     "zodiac":z,"moon_phase":mp,"moon_quad":mq,"retrograde":mr,
                     "wx_temp_mean":wx.get("t_mean"),"wx_temp_max":wx.get("t_max"),
                     "wx_precip":1 if wx.get("precip",0)>0 else 0,"wx_wind":wx.get("w_mean"),
                     "head":"special"})
    return pd.DataFrame(rows)
