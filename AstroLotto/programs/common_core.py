from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# utilities/common_core.py
# Shared helpers for recency-weighted fallback predictors.
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import pandas as pd

# Optional dependency on your existing features.py
try:
    from .features import load_history as _load_history, GAME_MAP as _GAME_MAP
except Exception:
    _load_history = None
    _GAME_MAP = {}

# Reasonable defaults if GAME_MAP isn't present
DEFAULT_GAME_MAP = {
    "powerball": {
        "white_cols": ["white_1","white_2","white_3","white_4","white_5"],
        "special": True, "special_col": "powerball",
        "white_max": 69, "special_max": 26
    },
    "mega_millions": {
        "white_cols": ["white_1","white_2","white_3","white_4","white_5"],
        "special": True, "special_col": "mega_ball",
        "white_max": 70, "special_max": 25
    },
    "cash5": {
        "white_cols": ["white_1","white_2","white_3","white_4","white_5"],
        "special": False, "white_max": 32
    },
    "lucky_for_life": {
        "white_cols": ["white_1","white_2","white_3","white_4","white_5"],
        "special": True, "special_col": "lucky_ball",
        "white_max": 48, "special_max": 18
    },
    "colorado_lottery": {
        # Colorado Lotto+ is typically 6 from 1..40, no special. We will select first k requested.
        "white_cols": ["white_1","white_2","white_3","white_4","white_5","white_6"],
        "special": False, "white_max": 40
    },
    "pick3": {
        # Treat as 3 numbers 0..9 (inclusive). We'll allow 0 as valid min.
        "white_cols": ["d1","d2","d3"],
        "special": False, "white_min": 0, "white_max": 9
    },
}

def GAME_INFO(game_key: str) -> Dict[str, Any]:
    g = (_GAME_MAP.get(game_key) if isinstance(_GAME_MAP, dict) else None) or {}
    d = DEFAULT_GAME_MAP.get(game_key, {})
    out = dict(d)
    out.update(g or {})
    # normalize
    out.setdefault("white_cols", ["white_1","white_2","white_3","white_4","white_5"])
    out.setdefault("special", False)
    out.setdefault("white_min", 1)
    out.setdefault("white_max", 69)
    if out.get("special"):
        out.setdefault("special_col", "special")
        out.setdefault("special_min", 1)
        out.setdefault("special_max", 26)
    return out

def decay_weights(n: int, half_life: int = 180) -> pd.Series:
    if n <= 0:
        return pd.Series([], dtype=float)
    ages = pd.Series(range(n-1, -1, -1), dtype=float)  # oldest..newest
    w = (-(math.log(2)) * (ages / max(1, half_life))).apply(math.exp)
    s = float(w.sum())
    return (w / s) if s > 0 else w

def weighted_counts(series: Iterable[int], weights: Iterable[float]) -> pd.Series:
    s = pd.Series(list(series), dtype="Int64")
    w = pd.Series(list(weights), dtype=float)
    if len(s) != len(w) or len(s) == 0:
        return pd.Series(dtype=float)
    df = pd.DataFrame({"n": s, "w": w}).dropna()
    if df.empty:
        return pd.Series(dtype=float)
    return df.groupby("n")["w"].sum().sort_values(ascending=False)

def select_top(counts: pd.Series, k: int, valid_min: int, valid_max: int, pinned: Optional[List[int]] = None) -> List[int]:
    pinned = [int(x) for x in (pinned or []) if isinstance(x, (int, float))]
    out: List[int] = []
    for p in pinned:
        if valid_min <= int(p) <= valid_max and int(p) not in out:
            out.append(int(p))
    if counts is None or counts.empty:
        x = valid_min
        while len(out) < k and x <= valid_max:
            if x not in out:
                out.append(x)
            x += 1
        return out[:k]
    for n in counts.index.tolist():
        n_int = int(n)
        if n_int not in out and valid_min <= n_int <= valid_max:
            out.append(n_int)
        if len(out) >= k:
            break
    return out[:k]

def _flex_history_fallback(game_key: str, root: Path) -> "pd.DataFrame":
    # Look for cached CSVs with flexible names
    import glob
    candidates = []
    # Common patterns
    for pat in [
        f"cached_{game_key}_data.csv",
        f"cached_{game_key.replace(' ', '_')}_data.csv",
        f"data_{game_key}.csv",
        f"{game_key}.csv",
    ]:
        candidates += glob.glob(str(root / pat))
        candidates += glob.glob(pat)
    for c in candidates:
        try:
            df = pd.read_csv(c)
            if len(df):
                return df
        except Exception:
            continue
    return pd.DataFrame()

def load_history(game_key: str, root_dir: Path) -> "pd.DataFrame":
    if callable(_load_history):
        try:
            return _load_history(game_key, root_dir)
        except Exception:
            pass
    return _flex_history_fallback(game_key, root_dir)

def generic_prediction(
    game_key: str,
    k_white: int,
    k_special: int = 0,
    *,
    root_dir: str | Path | None = None,
    pinned_whites: Optional[List[int]] = None,
    pinned_specials: Optional[List[int]] = None,
    half_life_draws: int = 180,
    white_min: Optional[int] = None,
    white_max: Optional[int] = None,
    special_min: Optional[int] = None,
    special_max: Optional[int] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    info = GAME_INFO(game_key)
    wmin = int(white_min if white_min is not None else info.get("white_min", 1))
    wmax = int(white_max if white_max is not None else info.get("white_max", 69))
    root = Path(root_dir) if root_dir is not None else Path(__file__).resolve().parent.parent
    df = load_history(game_key, root)

    # Assemble white series
    white_cols = info.get("white_cols", ["white_1","white_2","white_3","white_4","white_5"])
    work = df.copy()
    for c in white_cols:
        if c in work.columns:
            work[c] = pd.to_numeric(work[c], errors="coerce").astype("Int64")
    n = len(work)
    weights = decay_weights(n, half_life_draws)
    whites_series, weights_expanded = [], []
    if not work.empty:
        for w, (_, row) in zip(weights.tolist(), work.iterrows()):
            for c in white_cols:
                if c in work.columns and pd.notna(row.get(c)):
                    whites_series.append(int(row.get(c)))
                    weights_expanded.append(float(w))
    white_counts = weighted_counts(whites_series, weights_expanded)
    whites = select_top(white_counts, int(k_white), wmin, wmax, pinned=pinned_whites)

    result: Dict[str, Any] = {"white": whites}
    # Special handling if game has special and requested
    if info.get("special", False) and int(k_special) > 0:
        scol = info.get("special_col", "special")
        smin = int(special_min if special_min is not None else info.get("special_min", 1))
        smax = int(special_max if special_max is not None else info.get("special_max", 26))
        if scol in work.columns:
            s_series = pd.to_numeric(work[scol], errors="coerce").astype("Int64").dropna().astype(int).tolist()
            s_weights = decay_weights(len(s_series), half_life_draws)
            s_counts = weighted_counts(s_series, s_weights)
            s_pick = select_top(s_counts, 1, smin, smax, pinned=pinned_specials)
            if s_pick:
                result["special"] = int(s_pick[0])
    result["meta"] = {
        "backend": f"utilities.common_core.generic_prediction[{game_key}]",
        "history_rows": int(len(df)),
        "half_life_draws": int(half_life_draws),
        "white_range": [wmin, wmax],
        "used_white_cols": list(white_cols),
        "has_special": bool(info.get("special", False)),
    }
    return result
