from __future__ import annotations

import numpy as np, pandas as pd, re as _re
from typing import Dict, Optional

GAME_RULES: Dict[str, Dict[str, int]] = {
    "Powerball": {"white_max": 69, "special_max": 26},
    "Mega Millions": {"white_max": 70, "special_max": 25},
    "MegaMillions": {"white_max": 70, "special_max": 25},
    "Pick 3": {"white_max": 10, "special_max": 0},
    "Pick 4": {"white_max": 10, "special_max": 0},
    "Pick3": {"white_max": 10, "special_max": 0},
    "Pick4": {"white_max": 10, "special_max": 0},
}

def _key(game: str) -> str:
    return game if game in GAME_RULES else game.replace(" ", "")

def _norm(a, n: int):
    if a is None or len(a) != n:
        a = np.ones(n, dtype=float) / float(n)
    else:
        a = np.asarray(a, dtype=float)
        s = a.sum()
        a = a / s if s > 0 else np.ones(n, dtype=float) / float(n)
    return a

def _cols(df: pd.DataFrame, pat: str):
    return [c for c in df.columns if _re.search(pat, c, _re.I)]

def compute_number_probs(df: pd.DataFrame, game: str):
    rules = GAME_RULES.get(_key(game), {"white_max": 69, "special_max": 26})
    wm, sm = int(rules["white_max"]), int(rules.get("special_max") or 0)
    white = np.ones(wm, dtype=float); special = (np.ones(sm, dtype=float) if sm else None)

    if isinstance(df, pd.DataFrame) and not df.empty:
        wcols = _cols(df, r"(white|ball|num)")
        if wcols:
            freq = np.ones(wm, dtype=float)
            for c in wcols:
                vals = pd.to_numeric(df[c], errors="coerce").dropna().astype(int)
                for v in vals:
                    if 1 <= v <= wm: freq[v-1] += 1
            white = freq
        if sm:
            scols = _cols(df, r"(special|mega|power|bonus|pb|mb|gold)")
            if scols:
                freq = np.ones(sm, dtype=float)
                for c in scols:
                    vals = pd.to_numeric(df[c], errors="coerce").dropna().astype(int)
                    for v in vals:
                        if 1 <= v <= sm: freq[v-1] += 1
                special = freq

    return {"white": _norm(white, wm), "special": (_norm(special, sm) if sm else None)}
