from __future__ import annotations
"""
Developer panels for AstroLotto V14.

These helpers generate additional diagnostic output for interested users
when the ``show_dev_panels`` flag is enabled.  They intentionally
avoid altering any core prediction logic.  Panels may include
intermediate scores, sample sets from alternate engines, or other
introspection aids.

At present the module exposes a single function,
:func:`render_basic_panel`, which displays a simple table of numbers
ranked by their combined long/short and gap/overdue scores, plus a
few sample Monte Carlo sets.  This function is safe to call even
outside a Streamlit environment; it becomes a no‑op if the import
fails.
"""
from typing import Any, Dict, List

try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore

import pandas as pd

from .smart_features_v2 import WHITE_RANGES, long_short_blend, gap_overdue_bonus
from .montecarlo_v2 import monte_carlo_picks

def render_basic_panel(game: str, df: pd.DataFrame, max_numbers: int = 20) -> None:
    """
    Render a simple developer panel showing top numbers by combined
    long/short and gap scores, along with a sample of Monte Carlo
    sets.  Does nothing if Streamlit is unavailable.

    Parameters
    ----------
    game : str
        Name of the lottery game (e.g. ``"powerball"``).
    df : pandas.DataFrame
        History of past draws for the game.  Should contain at least
        the draw date and number columns required by the internal
        feature functions.  If empty or ``None`` the panel notes
        that a uniform distribution is assumed.
    max_numbers : int, optional
        How many top numbers to show (default 20).
    """
    if st is None:
        return
    # Header for the diagnostics panel.  Labelled as a Features Diagnostic
    # panel rather than a developer-only panel.  This conveys that the
    # content is optional and does not affect predictions.
    st.markdown("### Features Diagnostics: Top Numbers and Monte Carlo Samples")
    try:
        lo, hi, _ = WHITE_RANGES.get(game, (1, 70, 5))
        if df is None or df.empty:
            candidates = list(range(lo, hi + 1))
            st.write("No history available. Uniform distribution assumed.")
            st.write("Sample numbers:", candidates[:max_numbers])
            return
        # compute combined scores
        base = long_short_blend(df, game, short_days=30, alpha=0.3)
        gap = gap_overdue_bonus(df, game, strength=0.2)
        combined: Dict[int, float] = {i: float(base.get(i, 0.0)) * float(gap.get(i, 1.0)) for i in range(lo, hi + 1)}
        top = sorted(combined.items(), key=lambda kv: (-kv[1], kv[0]))[:max_numbers]
        st.write("**Top numbers by long/short × gap (first 20):**")
        st.dataframe(pd.DataFrame(top, columns=["Number", "Score"]))
        # show Monte Carlo samples
        try:
            msets: List[List[int]] = monte_carlo_picks(
                game, df,
                n_sets=5, n_sims=2000,
                short_days=30, alpha=0.3,
                gap_strength=0.2, chaos_pct=0.05,
                use_time_decay=False, lam=0.02,
                use_wrs=True, use_pmi=True
            )
            if msets:
                st.write("**Sample Monte Carlo sets (top 5):**")
                for idx, s in enumerate(msets, 1):
                    st.write(f"Set {idx}: {s}")
        except Exception as mc_err:
            st.info(f"Monte Carlo sample unavailable: {mc_err}")
    except Exception as e:
        st.info(f"Dev panel error: {e}")

__all__ = ["render_basic_panel"]