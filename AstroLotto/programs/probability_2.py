from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/probability.py (v1.2 context-aware)
import math, os
from typing import Dict, Optional, Tuple, List
import numpy as np
import pandas as pd

GAME_RULES = {
    "powerball":   {"k_white": 5, "white_min": 1, "white_max": 69, "special_min": 1, "special_max": 26},
    "megamillions":{"k_white": 5, "white_min": 1, "white_max": 70, "special_min": 1, "special_max": 25},
    "colorado_lottery": {"k_white": 6, "white_min": 1, "white_max": 40, "special_min": None, "special_max": None},
    "cash5": {"k_white": 5, "white_min": 1, "white_max": 32, "special_min": None, "special_max": None},
    "pick3": {"k_white": 3, "white_min": 0, "white_max": 9, "special_min": None, "special_max": None},
    "lucky_for_life":{"k_white": 5, "white_min": 1, "white_max": 48, "special_min": 1, "special_max": 18},
}

def _norm_game(game: str) -> str:
    g = (game or "").lower().strip()
    if g.startswith("power"): return "powerball"
    if g.startswith("mega"): return "megamillions"
    if "colorado" in g and "lotto" in g: return "colorado_lottery"
    if g in ("cash5","cash 5"): return "cash5"
    if g.replace(" ", "") in ("lfl","luckyforlife"): return "lucky_for_life"
    return g

def _date_col(df: pd.DataFrame) -> Optional[str]:
    for c in ("draw_date","date","Date"):
        if c in df.columns: return c
    return None

def _exp_weights(dates: pd.Series, halflife_days: float) -> np.ndarray:
    if dates.empty: return np.array([])
    maxd = pd.to_datetime(dates).max()
    deltas = (pd.to_datetime(maxd) - pd.to_datetime(dates)).dt.total_seconds() / (3600*24)
    lam = math.log(2.0) / max(1e-9, halflife_days)
    return np.exp(-lam * deltas.values.astype(float))

def _context_weights(df: pd.DataFrame, context: Optional[Dict]) -> np.ndarray:
    if not context: return np.ones(len(df), dtype=float)
    ctx_q = context.get("moon_quadrant", None)
    if ctx_q is None: return np.ones(len(df), dtype=float)
    col = None
    for c in ("moon_quadrant","moon_q","moonquad"):
        if c in df.columns: col=c; break
    if col is None: return np.ones(len(df), dtype=float)
    q = pd.to_numeric(df[col], errors="coerce").fillna(-1).astype(int).values
    return np.where(q == int(ctx_q), 1.25, 1.0)

def _guess_cols(df: pd.DataFrame, game: str) -> Tuple[List[str], Optional[str]]:
    cols = [c.lower() for c in df.columns]; mapping = dict(zip(cols, df.columns))
    white_names = ["white1","white2","white3","white4","white5","white6","n1","n2","n3","n4","n5","n6","w1","w2","w3","w4","w5","w6","ball1","ball2","ball3","ball4","ball5","ball6"]
    special_names = ["powerball","power","pb","mega","megaball","bonus","special"]
    whites=[mapping[n] for n in white_names if n in mapping][:GAME_RULES.get(game,{}).get("k_white",5)]
    special=None
    for n in special_names:
        if n in mapping: special = mapping[n]; break
    return whites, special

def compute_number_probs(df: pd.DataFrame, game: str, halflife_days: float=180.0, smoothing_white: float=1.0, smoothing_special: float=1.0, rule_clip: bool=True, context: Optional[Dict]=None) -> Dict[str, np.ndarray]:
    game = _norm_game(game)
    rules = GAME_RULES[game]
    k_white = rules["k_white"]; wmin,wmax = rules["white_min"], rules["white_max"]
    smin,smax = rules["special_min"], rules["special_max"]
    dc = _date_col(df)
    if dc is None: raise ValueError("No date column (draw_date/date/Date).")
    whites_c, special_c = _guess_cols(df, game)

    w_time = _exp_weights(df[dc], halflife_days)
    w_ctx = _context_weights(df, context)
    weights = w_time * w_ctx
    if weights.size == 0:
        whites_probs = np.full(wmax - wmin + 1, 1.0/(wmax - wmin + 1))
        special_probs = None if smin is None else np.full(smax - smin + 1, 1.0/(smax - smin + 1))
        return {"white": whites_probs, "special": special_probs}

    white_counts = np.zeros(wmax - wmin + 1, dtype=float)
    special_counts = None if smin is None else np.zeros(smax - smin + 1, dtype=float)
    for i, (_, row) in enumerate(df.iterrows()):
        w = float(weights[i])
        for c in whites_c:
            try:
                n = int(row[c]); 
                if not rule_clip or (wmin<=n<=wmax): white_counts[n - wmin] += w
            except Exception:
                continue
        if special_counts is not None and special_c is not None:
            try:
                sp = int(row[special_c]); 
                if not rule_clip or (smin<=sp<=smax): special_counts[sp - smin] += w
            except Exception:
                continue

    white_scores = white_counts + smoothing_white
    white_probs = white_scores / white_scores.sum()
    special_probs = None
    if special_counts is not None:
        s = special_counts + smoothing_special
        special_probs = s / (s.sum() if s.sum()>0 else 1.0)
    return {"white": white_probs, "special": special_probs}
