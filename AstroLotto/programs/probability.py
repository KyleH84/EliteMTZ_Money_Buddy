from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/probability.py (v1.3)
import math
import numpy as np, pandas as pd

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

def _date_col(df: pd.DataFrame):
    for c in ("draw_date","date","Date"):
        if c in df.columns: return c
    return None

def _exp_weights(dates: pd.Series, halflife_days: float=180.0) -> np.ndarray:
    if dates.empty: return np.array([])
    maxd = pd.to_datetime(dates).max()
    deltas = (pd.to_datetime(maxd) - pd.to_datetime(dates)).dt.total_seconds()/86400.0
    lam = math.log(2.0) / max(1e-9, halflife_days)
    return np.exp(-lam * deltas.values.astype(float))

def compute_number_probs(df: pd.DataFrame, game: str, halflife_days: float=180.0):
    g=_norm_game(game)
    rules = GAME_RULES[g]
    k = rules["k_white"]; wmin,wmax = rules["white_min"], rules["white_max"]
    smin,smax = rules["special_min"], rules["special_max"]
    dc = _date_col(df)
    if dc is None: raise ValueError("No date column")
    weights = _exp_weights(df[dc], halflife_days)
    if weights.size == 0:
        white = np.full(wmax-wmin+1, 1.0/(wmax-wmin+1))
        special = None if smin is None else np.full(smax-smin+1, 1.0/(smax-smin+1))
        return {"white": white, "special": special}
    counts_white = np.zeros(wmax-wmin+1, dtype=float)
    counts_special = None if smin is None else np.zeros(smax-smin+1, dtype=float)
    # Best-effort white/special column inference
    whites_c = [c for c in df.columns if str(c).lower() in {"white1","white2","white3","white4","white5","white6","n1","n2","n3","n4","n5","n6","ball1","ball2","ball3","ball4","ball5","ball6"}][:k]
    special_c = next((c for c in df.columns if str(c).lower() in {"powerball","power","pb","mega","megaball","bonus","special"}), None)
    for i, (_, row) in enumerate(df.iterrows()):
        w = float(weights[i])
        for c in whites_c:
            try:
                n = int(row[c])
                if wmin<=n<=wmax: counts_white[n-wmin]+=w
            except Exception: pass
        if counts_special is not None and special_c is not None:
            try:
                sp = int(row[special_c])
                if smin<=sp<=smax: counts_special[sp-smin]+=w
            except Exception: pass
    white = counts_white + 1.0
    white = white / white.sum()
    special = None
    if counts_special is not None:
        s = counts_special + 1.0
        special = s / (s.sum() if s.sum()>0 else 1.0)
    return {"white": white, "special": special}
