from __future__ import annotations
"""
Monte Carlo predictor wrapper for AstroLotto V14.

This module exposes a simple function :func:`predict_sets` which
invokes the Monte Carlo sampler defined in
``utilities.montecarlo_v2``.  It converts the sampled white ball sets
into the prediction dictionary format expected by the UI and chooses
a special ball when applicable.

The function accepts a variety of parameters controlling the number of
simulations, blend windows, gap strength, chaos percentage, and
pair/weighted sampling options.  Reasonable defaults are provided
matching the Smart 2.0 settings used elsewhere in the app.
"""
from typing import List, Dict, Any
import pandas as pd

from ..utilities.smart_features_v2 import WHITE_RANGES
from ..utilities.montecarlo_v2 import monte_carlo_picks, choose_special  # type: ignore

def predict_sets(
    game: str,
    df: pd.DataFrame,
    n_sets: int = 3,
    *,
    n_sims: int = 5000,
    short_days: int = 30,
    alpha: float = 0.3,
    gap_strength: float = 0.2,
    chaos_pct: float = 0.05,
    use_time_decay: bool = False,
    lam: float = 0.02,
    use_wrs: bool = True,
    use_pmi: bool = True,
    notes: str = "montecarlo",
) -> List[Dict[str, Any]]:
    """
    Generate ``n_sets`` prediction sets using the Monte Carlo engine.

    Parameters
    ----------
    game : str
        Lottery game name.
    df : pandas.DataFrame
        Past draw history for the game.  If empty, a uniform base will
        be assumed by the underlying engine.
    n_sets : int, optional
        Number of prediction sets to return (default 3).
    n_sims : int, optional
        Number of Monte Carlo simulations to perform (default 5000).
    short_days : int, optional
        Window size in days for the short-term component (default 30).
    alpha : float, optional
        Blend weight between short- and long-term components (default 0.3).
    gap_strength : float, optional
        Strength of gap/overdue bonuses (default 0.2).
    chaos_pct : float, optional
        Fraction of the domain to perturb with chaos (default 0.05).
    use_time_decay : bool, optional
        Whether to weight historical draws exponentially (default False).
    lam : float, optional
        Decay rate used when ``use_time_decay`` is true (default 0.02).
    use_wrs : bool, optional
        Whether to sample numbers without replacement (default True).
    use_pmi : bool, optional
        Whether to apply PMI pair synergy (default True).
    notes : str, optional
        Notes field added to each prediction dict (default 'montecarlo').

    Returns
    -------
    list of dict
        Each dict has keys ``"white"``, ``"special"``, and
        ``"notes"``.  The ``"white"`` value is a sorted list of
        integers; ``"special"`` may be ``None`` if the game has no
        special ball.
    """
    if df is None:
        df = pd.DataFrame()
    # Determine white ball domain and sample sets
    lo, hi, k = WHITE_RANGES.get(game, (1, 70, 5))
    # Underlying Monte Carlo yields a ranked list of candidate sets; we take n_sets
    mc_sets = monte_carlo_picks(
        game,
        df,
        n_sets=max(int(n_sets), 1),
        n_sims=int(n_sims),
        short_days=int(short_days),
        alpha=float(alpha),
        gap_strength=float(gap_strength),
        chaos_pct=float(chaos_pct),
        use_time_decay=bool(use_time_decay),
        lam=float(lam),
        use_wrs=bool(use_wrs),
        use_pmi=bool(use_pmi),
    ) or []
    picks: List[Dict[str, Any]] = []
    # Convert each sampled set into a pick dict
    for s in mc_sets[:max(int(n_sets), 1)]:
        s_sorted = sorted(int(x) for x in s)
        sp = choose_special(game, df, None)
        picks.append({"white": s_sorted, "special": sp, "notes": notes})
    return picks

__all__ = ["predict_sets"]