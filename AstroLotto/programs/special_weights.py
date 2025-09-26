from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/special_weights.py
from typing import Dict, Tuple
import pandas as pd
from collections import Counter

SPECIAL_META: Dict[str, Tuple[str, int]] = {
    "powerball": ("powerball", 26),        # column name (best-guess), max value
    "megamillions": ("mega_ball", 25),
    "luckyforlife": ("lucky_ball", 18),
}

# Accept common aliases per game
ALIASES = {
    "powerball": ["powerball","pb","special"],
    "megamillions": ["mega_ball","megaball","mega","special"],
    "luckyforlife": ["lucky_ball","luckyball","lucky","special"],
}

def detect_special_column(df: pd.DataFrame, game: str) -> str | None:
    if df is None or df.empty:
        return None
    game = game.lower().replace(" ", "")
    cand = SPECIAL_META.get(game, (None, None))[0]
    cols = [c for c in df.columns]
    if cand and cand in cols:
        return cand
    for alias in ALIASES.get(game, []):
        if alias in cols:
            return alias
        # tolerance for case/underscore
        for c in cols:
            if c.replace("_","").lower() == alias:
                return c
    # fallback: any column that looks integer and not a "white" column
    for c in cols:
        lc = c.lower()
        if lc=="draw_date" or lc.startswith("white") or lc in ("n1","n2","n3","n4","n5","n6"):
            continue
        try:
            s = pd.to_numeric(df[c], errors="coerce").dropna().astype(int)
            if (s>=1).all():
                # pick the most plausible one
                return c
        except Exception:
            continue
    return None

def compute_special_scores(df: pd.DataFrame, game: str) -> Dict[int, float] | None:
    col = detect_special_column(df, game)
    if not col:
        return None
    series = pd.to_numeric(df[col], errors="coerce").dropna().astype(int)
    if series.empty:
        return None
    maxv = SPECIAL_META.get(game, (None, None))[1]
    cnt = Counter(series.tolist())
    # laplace smoothing
    scores: Dict[int, float] = {}
    if maxv:
        total = 0.0
        for k in range(1, maxv+1):
            v = cnt.get(k, 0) + 1.0
            scores[k] = v
            total += v
        for k in scores:
            scores[k] = scores[k] / total
    else:
        total = sum(cnt.values()) + len(cnt)
        for k in cnt:
            scores[int(k)] = (cnt[k] + 1.0) / total
    return scores
