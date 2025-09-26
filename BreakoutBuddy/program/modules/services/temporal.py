from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import pandas as pd
from modules.temporal_agent import TemporalAgent, KozyrevConfig

def time_sensitivity(row) -> float:
    """Compute a time-sensitivity scalar for a single row if possible."""
    try:
        agent = TemporalAgent(KozyrevConfig())
        return float(agent.score_row(row))
    except Exception:
        return 1.0

def apply_temporal_correction(scores: pd.Series, settings=None) -> pd.Series:
    """Apply a gentle temporal correction to a score series (noop-safe)."""
    try:
        # Placeholder: keep identity for now; real logic can be slotted later.
        return scores
    except Exception:
        return scores
