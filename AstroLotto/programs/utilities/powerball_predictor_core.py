
# utilities/powerball_predictor_core.py
# Lightweight backend for Powerball when ML backends are unavailable.
# Exposes get_powerball_prediction(root_dir, k_white=5, k_special=1)
# to satisfy the app's dynamic loader.

from __future__ import annotations
from typing import Dict, List
import math
import pandas as pd

try:
    # When placed under `utilities/`, this relative import works
    from .features import load_history
except Exception:
    # Allow running as a standalone module for testing
    from utilities.features import load_history  # type: ignore

WHITE_MIN, WHITE_MAX = 1, 69
SPEC_MIN, SPEC_MAX   = 1, 26

def _decay_weights(n: int, half_life: int = 180) -> pd.Series:
    """Return length-n vector of recency decay weights (newest has highest weight).
    Weight_t = exp(-ln(2) * age / half_life)
    where age=0 for the newest draw.
    """
    if n <= 0:
        return pd.Series([], dtype=float)
    ages = pd.Series(range(n-1, -1, -1), dtype=float)  # oldest .. newest
    w = (-(math.log(2)) * (ages / max(1, half_life))).apply(math.exp)
    # normalize to sum to 1 to keep scores comparable across datasets
    s = float(w.sum())
    return (w / s) if s > 0 else w

def _score_numbers(series: pd.Series, weights: pd.Series, lo: int, hi: int) -> pd.Series:
    """Return a score per number in [lo, hi] as weighted frequency."""
    # Build a DataFrame of [value, weight] rows for fast groupby
    df = pd.DataFrame({'val': series.astype('Int64'), 'w': weights})
    df = df.dropna()
    if df.empty:
        return pd.Series({i: 0.0 for i in range(lo, hi+1)}, dtype=float)
    scores = df.groupby('val')['w'].sum()
    # Ensure all numbers exist in the index
    for i in range(lo, hi+1):
        if i not in scores.index:
            scores.loc[i] = 0.0
    return scores.sort_index()

def _top_k(scores: pd.Series, k: int) -> List[int]:
    k = max(0, int(k))
    if k == 0 or scores.empty:
        return []
    # Descending by score; stable by number ascending to keep determinism
    return (
        scores.sort_values(ascending=False)
              .sort_index(kind='mergesort')  # stable secondary by index
              .head(k)
              .index.astype(int)
              .tolist()
    )

def get_powerball_prediction(root_dir: str, k_white: int = 5, k_special: int = 1) -> Dict[str, object]:
    """Return a Powerball prediction using recency‑weighted frequency.

    Parameters
    ----------
    root_dir : str
        Project root (folder that contains the cached_* CSVs).
    k_white : int
        How many white balls to suggest (typically 5).
    k_special : int
        How many Powerballs to suggest (typically 1).

    Returns
    -------
    dict with keys:
        white: List[int]
        special: List[int]
        method: str
        scores_white: Dict[int, float]  (useful for UI explanation/heatmaps)
        scores_special: Dict[int, float]
    """
    hist = load_history("powerball", root_dir)
    if hist.empty:
        # Graceful fallback with no history
        return {
            "white": [],
            "special": [],
            "method": "recency_weighted_frequency:no_history",
            "scores_white": {i: 0.0 for i in range(WHITE_MIN, WHITE_MAX+1)},
            "scores_special": {i: 0.0 for i in range(SPEC_MIN, SPEC_MAX+1)},
        }

    # Build chronologically increasing order and aligned weights
    hist = hist.sort_values("date").reset_index(drop=True)
    n = len(hist)
    w = _decay_weights(n, half_life=180)  # tweakable in settings later

    # Collect all white numbers into a single long series aligned with weights
    white_cols = [c for c in hist.columns if c.lower().startswith("n")]
    long_white_vals = []
    long_white_w = []
    for idx, row in hist.iterrows():
        for c in white_cols:
            try:
                v = int(row[c])
            except Exception:
                continue
            long_white_vals.append(v)
            long_white_w.append(w.iloc[idx])
    if long_white_vals:
        white_scores = pd.Series(long_white_w, index=pd.Index(long_white_vals, name="val")).groupby(level=0).sum()
    else:
        white_scores = pd.Series(dtype=float)

    # Special ball column commonly named s1
    special_vals = []
    special_w = []
    s_col = "s1" if "s1" in hist.columns else None
    if s_col is None:
        # Try to infer a special column name if history headers differ
        candidates = [c for c in hist.columns if c.lower() in ("pb", "powerball", "special", "bonus", "s")]
        if candidates:
            s_col = candidates[0]
    if s_col:
        for idx, row in hist.iterrows():
            try:
                v = int(row[s_col])
            except Exception:
                continue
            special_vals.append(v)
            special_w.append(w.iloc[idx])
    if special_vals:
        special_scores = pd.Series(special_w, index=pd.Index(special_vals, name="val")).groupby(level=0).sum()
    else:
        special_scores = pd.Series(dtype=float)

    # Ensure domains present
    for i in range(WHITE_MIN, WHITE_MAX+1):
        if i not in white_scores.index:
            white_scores.loc[i] = 0.0
    for i in range(SPEC_MIN, SPEC_MAX+1):
        if i not in special_scores.index:
            special_scores.loc[i] = 0.0

    white_pick = _top_k(white_scores.sort_index(), k_white)
    special_pick = _top_k(special_scores.sort_index(), k_special)

    return {
        "white": white_pick,
        "special": special_pick,
        "method": "recency_weighted_frequency:half_life=180",
        "scores_white": {int(i): float(s) for i, s in white_scores.items()},
        "scores_special": {int(i): float(s) for i, s in special_scores.items()},
    }
