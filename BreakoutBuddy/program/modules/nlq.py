from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import pandas as pd
import re

ALIASES = {
    "price":"Close",
    "close":"Close",
    "rsi2":"RSI2",
    "rsi4":"RSI4",
    "connors":"ConnorsRSI",
    "rel":"RelSPY",
    "rvol":"RVOL",
    "atr":"ATR",
    "crowd":"CrowdRisk",
    "retail":"RetailChaseRisk",
    "squeeze":"SqueezeHint",
    "pct200":"PctFrom200d",
}

OPS = {"<":"<", ">":">", "<=":"<=", ">=":">=", "==":"==", "!=":"!="}

def parse_query_to_filters(q: str):
    tokens = re.split(r"\s+and\s+|\s*,\s*", q.strip(), flags=re.I)
    conds = []
    for tok in tokens:
        m = re.match(r"([a-zA-Z_]+)\s*(<=|>=|==|!=|<|>)\s*(-?\d+(\.\d+)?)", tok.strip())
        if not m: 
            continue
        key, op, val = m.group(1).lower(), m.group(2), float(m.group(3))
        col = ALIASES.get(key, key)
        if op not in OPS: 
            continue
        conds.append((col, op, val))
    return conds

def apply_filters(df: pd.DataFrame, conds):
    mask = pd.Series(True, index=df.index)
    for col, op, val in conds:
        if col not in df.columns: 
            continue
        if op == "<":  mask &= df[col] < val
        elif op == ">": mask &= df[col] > val
        elif op == "<=": mask &= df[col] <= val
        elif op == ">=": mask &= df[col] >= val
        elif op == "==": mask &= df[col] == val
        elif op == "!=": mask &= df[col] != val
    return df[mask]
