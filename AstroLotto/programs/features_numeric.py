# Program/utilities/features_numeric.py
from __future__ import annotations
from typing import Tuple, Dict, List
import numpy as np
import pandas as pd

def rules_for_game(game: str) -> Tuple[int,int,int,int|None,int|None]:
    g = (game or "").lower()
    if g.startswith("power"): return 5,1,69,1,26
    if g.startswith("mega"):  return 5,1,70,1,25
    if "colorado" in g:       return 6,1,40,None,None
    if "cash5" in g:          return 5,1,32,None,None
    if "lucky" in g:          return 5,1,48,1,18
    if "pick3" in g:          return 3,0,9,None,None
    return 5,1,70,1,26

def _date_col(df: pd.DataFrame) -> str|None:
    for c in ("draw_date","date","Date"):
        if c in df.columns: return c
    return None

def last_seen_gap(df: pd.DataFrame, dc: str, whites: List[str]) -> Dict[int,int]:
    # days since number was seen among white columns
    ser = {}
    if df.empty: return ser
    bydate = df.sort_values(dc)
    last_idx = {}
    for idx, row in bydate.iterrows():
        d = pd.to_datetime(row[dc])
        for c in whites:
            try:
                n = int(row[c])
                last_idx[n] = d
            except Exception:
                continue
    maxd = pd.to_datetime(bydate[dc]).max()
    for n, dt in last_idx.items():
        ser[int(n)] = int((maxd - dt).days)
    return ser

def rolling_freq(df: pd.DataFrame, whites: List[str], window: int, wmin: int, wmax: int) -> Dict[int,float]:
    if df.empty: return {}
    tail = df.tail(window) if window>0 else df
    counts = {i:0 for i in range(wmin, wmax+1)}
    for _,row in tail.iterrows():
        for c in whites:
            try:
                n = int(row[c])
                if wmin<=n<=wmax: counts[n]+=1
            except Exception:
                continue
    total = sum(counts.values())
    if total==0: total=1
    return {k: v/total for k,v in counts.items()}
