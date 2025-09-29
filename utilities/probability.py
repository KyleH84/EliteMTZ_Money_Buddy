from __future__ import annotations

# Robust shim so imports like `from utilities.probability import ...` always resolve.
# Priority:
#   1) AstroLotto.programs.utilities.probability  (AL-local)
#   2) src.shared.utilities.probability           (shared lib, if present)
#   3) Minimal fallback implementations (keeps app running)

try:
    # 1) Prefer AstroLotto's local implementation
    from AstroLotto.programs.utilities.probability import *  # type: ignore
except Exception:
    try:
        # 2) Fall back to shared implementation
        from src.shared.utilities.probability import *  # type: ignore
    except Exception:
        # 3) Minimal fallback so the app does not crash
        import numpy as _np
        from typing import Dict, Any

        GAME_RULES: Dict[str, Dict[str, int]] = {
            "MegaMillions": {"white_max": 70, "special_max": 25},
            "Powerball": {"white_max": 69, "special_max": 26},
        }

        def _uniform_probs(n: int):
            if n <= 0:
                return None
            arr = _np.full(n, 1.0 / n, dtype=float)
            return arr

        def compute_number_probs(history, game: str) -> Dict[str, Any]:
            rules = GAME_RULES.get(game, {"white_max": 69, "special_max": 26})
            return {
                "white": _uniform_probs(int(rules.get("white_max", 69))),
                "special": _uniform_probs(int(rules.get("special_max", 26))),
            }
