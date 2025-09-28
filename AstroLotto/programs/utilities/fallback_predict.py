from __future__ import annotations

from typing import Optional, Sequence, Tuple, Dict
import numpy as np
import pandas as pd

# Use AL-local utilities only
from .probability import compute_number_probs, GAME_RULES


def fallback_predict(
    game: str,
    history: Optional[pd.DataFrame] = None,
    n_white: int = 5,
    n_special: int = 1,
    seed: Optional[int] = None,
) -> Tuple[Sequence[int], Sequence[int]]:
    """Conservative, dependency-free fallback pick generator.

    - Uses frequency-weighted probabilities from historical draws when provided.
    - Falls back to uniform sampling within the legal game ranges.
    - Never imports BreakoutBuddy; stays inside AstroLotto utilities.

    Returns:
        (whites, specials) as sorted integer sequences.
    """
    rules: Dict[str, Dict[str, int]] = GAME_RULES
    key = game if game in rules else game.replace(" ", "")
    rule = rules.get(key, {"white_max": 69, "special_max": 26})

    white_max = int(rule["white_max"])
    special_max = int(rule.get("special_max", 0) or 0)

    # If history provided, compute weighted probabilities; else uniform.
    if isinstance(history, pd.DataFrame) and not history.empty:
        probs = compute_number_probs(history, game)
        p_white = probs["white"]
        p_special = probs["special"]
    else:
        p_white = np.full(white_max, 1.0 / white_max)
        p_special = np.full(special_max, 1.0 / special_max) if special_max else None

    rng = np.random.default_rng(seed)

    whites = rng.choice(
        np.arange(1, white_max + 1),
        size=min(n_white, white_max),
        replace=False,
        p=p_white,
    )
    specials: Sequence[int] = []
    if special_max and p_special is not None and n_special > 0:
        specials = rng.choice(
            np.arange(1, special_max + 1),
            size=min(n_special, special_max),
            replace=False,
            p=p_special,
        )

    return sorted(whites.tolist()), sorted(list(specials))
