from __future__ import annotations
"""
Ensemble predictor for AstroLotto V14.

This module implements a lightweight ensemble engine that blends
long/short window statistics with optional gap/overdue bonuses and
pair synergy.  The resulting weights are used with a weighted random
sampler without replacement to generate sets of numbers.  A special
ball is chosen using the existing ``utilities.montecarlo_v2`` helper.

The ensemble engine is intentionally simple: it reuses existing
feature functions from ``utilities.smart_features_v2`` and uses
``utilities.wrs.weighted_wrs`` for sampling.  It does not depend
directly on Streamlit or any UI.  Callers are responsible for
providing the past draw history DataFrame and passing user-selected
parameters such as the short window, blend alpha, gap strength, and
pair synergy flag.
"""
from typing import Dict, Any, List
import random
import pandas as pd

from ..utilities.smart_features_v2 import (
    WHITE_RANGES,
    SPECIAL_RANGES,
    long_short_blend,
    gap_overdue_bonus,
    compute_special_scores,
)
from ..utilities.wrs import weighted_wrs
from ..utilities.pmi import pmi_pairs

def _choose_special(game: str, df: pd.DataFrame, model: Dict[str, Any] | None = None) -> int | None:
    """
    Select a special ball for ``game`` using the base special score
    computation from ``smart_features_v2``.  If no special range
    exists for the game (e.g. Cash 5), ``None`` is returned.

    Parameters
    ----------
    game : str
        Lottery game name.
    df : pandas.DataFrame
        Past draw history for the game.
    model : dict, optional
        Optional model dictionary; if provided and contains
        ``"special_scores"`` the scores will be used instead of
        recomputing them.

    Returns
    -------
    int or None
        Selected special ball value or ``None`` if the game does not
        have a special ball.
    """
    # Determine the range of the special ball
    lo_hi = SPECIAL_RANGES.get(game)
    if not lo_hi:
        return None
    lo, hi = lo_hi
    scores = None
    if isinstance(model, dict):
        scores = model.get("special_scores")
    if not scores:
        scores = compute_special_scores(df, game)
    keys = list(range(lo, hi + 1))
    w = [max(1e-9, float(scores.get(i, 0.0))) for i in keys]
    total = sum(w) or 1.0
    r = random.random() * total
    c = 0.0
    for val, wi in zip(keys, w):
        c += wi
        if r <= c:
            return val
    return keys[-1]

def predict_sets(
    game: str,
    df: pd.DataFrame,
    n_sets: int = 3,
    *,
    short_days: int = 30,
    alpha: float = 0.3,
    gap_strength: float = 0.2,
    use_pmi: bool = False,
    notes: str = "ensemble",
) -> List[Dict[str, Any]]:
    """
    Generate ``n_sets`` prediction sets using the ensemble engine.

    The engine computes base scores using a long/short blend.  If
    ``gap_strength`` is greater than zero the base scores are
    multiplied by gap/overdue bonuses.  If ``use_pmi`` is true a
    pairwise mutual information lookup is applied to nudge weights
    favouring historically correlated pairs.  The weighted random
    sampler then selects K white balls for each set without
    replacement.  The special ball is chosen via
    :func:`_choose_special`.

    Parameters
    ----------
    game : str
        Lottery game name (e.g. ``"powerball"``).
    df : pandas.DataFrame
        Past draw history for the game.  Should contain at least the
        columns expected by ``long_short_blend``.
    n_sets : int, optional
        Number of prediction sets to return (default 3).
    short_days : int, optional
        Window size in days for the short-term component (default 30).
    alpha : float, optional
        Blend weight between short- and long-term components (default 0.3).
    gap_strength : float, optional
        Strength of gap/overdue bonuses; 0 disables gap bonuses
        completely (default 0.2).
    use_pmi : bool, optional
        Whether to apply pair synergy using PMI (default False).
    notes : str, optional
        Notes field added to each prediction dict (default 'ensemble').

    Returns
    -------
    list of dict
        Each dict has keys ``"white"``, ``"special"``, and
        ``"notes"``.  The ``"white"`` value is a sorted list of
        integers; ``"special"`` may be ``None`` if the game has no
        special ball.
    """
    # Determine domain of white balls
    lo, hi, k = WHITE_RANGES.get(game, (1, 70, 5))
    if df is None:
        df = pd.DataFrame()
    # Compute base scores via long/short blend
    base_scores = long_short_blend(df, game, short_days=short_days, alpha=alpha)
    # Apply gap bonuses if requested
    if gap_strength > 0:
        gap = gap_overdue_bonus(df, game, strength=gap_strength)
        for i in range(lo, hi + 1):
            base_scores[i] = float(base_scores.get(i, 0.0)) * float(gap.get(i, 1.0))
    # Ensure no zero weights
    weights = {i: max(1e-9, float(base_scores.get(i, 0.0))) for i in range(lo, hi + 1)}
    # Precompute pair bonuses if requested
    pair_bonus: Dict[tuple[int, int], float] = {}
    if use_pmi:
        try:
            pair_bonus = pmi_pairs(df, lo, hi) or {}
        except Exception:
            pair_bonus = {}
    # Generate sets
    picks: List[Dict[str, Any]] = []
    for _ in range(max(1, int(n_sets))):
        # For each set we build a local weight map that applies pair bonuses dynamically
        remaining = list(range(lo, hi + 1))
        chosen: List[int] = []
        for _ in range(k):
            # Build local weights for remaining items
            loc_weights = {}
            for i in remaining:
                w = weights[i]
                # If we have already chosen numbers, apply pair synergy
                if use_pmi and chosen and pair_bonus:
                    bump = 1.0
                    for c in chosen:
                        a, b = (c, i) if c < i else (i, c)
                        if (a, b) in pair_bonus:
                            # amplify weight by PMI value scaled
                            bump *= (1.0 + 0.25 * pair_bonus[(a, b)])
                    w *= bump
                loc_weights[i] = w
            # Sample one number without replacement
            pick = weighted_wrs(remaining, loc_weights, 1)[0]
            chosen.append(pick)
            remaining.remove(pick)
        chosen_sorted = sorted(chosen)
        sp = _choose_special(game, df)
        picks.append({"white": chosen_sorted, "special": sp, "notes": notes})
    return picks

__all__ = ["predict_sets"]