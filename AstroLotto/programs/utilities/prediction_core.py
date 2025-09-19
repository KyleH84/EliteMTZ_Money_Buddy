
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json

# Local imports kept minimal to reduce risk
from .smart_predict_v2 import predict_sets_v2  # Monte Carlo + long/short + gap + PMI + diversity
from .smart_features import WHITE_RANGES, SPECIAL_RANGES, detect_white_columns
from .diversity import select_diverse

# Config flags from Extras/v14_flags.json
def _load_flags(root: Path) -> Dict[str, Any]:
    try:
        flags_path = root / "extras" / "v14_flags.json"
        if not flags_path.exists():
            flags_path = root / "Extras" / "v14_flags.json"
        if flags_path.exists():
            return json.loads(flags_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _flag(flags: Dict[str, Any], key: str, default: Any) -> Any:
    v = flags.get(key)
    return default if v is None else v

def _safe_read_csv(p: Path):
    import pandas as pd
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()

def _cache_path(root: Path, game: str) -> Path:
    name = {
        "powerball": "cached_powerball_data.csv",
        "megamillions": "cached_megamillions_data.csv",
        "cash5": "cached_cash5_data.csv",
        "pick3": "cached_pick3_data.csv",
        "luckyforlife": "cached_luckyforlife_data.csv",
        "colorado": "cached_colorado_lottery_data.csv",
    }[game]
    return (root / "Data" / name)

def _oracle_multiplier(kwargs: Dict[str, Any]) -> float:
    # Use Astro toggle as a proxy; default gentle
    use_astro = bool(kwargs.get("use_astro", False) or kwargs.get("oracle_on", False))
    return 1.0 + (0.10 if use_astro else 0.0)

def _n_sets(kwargs: Dict[str, Any]) -> int:
    # UI tends to pass n or n_picks
    for k in ("n", "n_picks", "num_tickets"):
        if k in kwargs:
            try: return max(1, int(kwargs[k]))
            except Exception: pass
    return 3

def _clamp_special(game: str, x: Optional[int]) -> Optional[int]:
    if x is None: return None
    lo, hi = SPECIAL_RANGES.get(game, (None, None))
    if lo is None: return x
    if x < lo or x > hi: return None
    return x

def _delegate_original(game: str, root: Path, **kwargs):
    # call original *predictor_core if available
    mod_map = {
        "powerball": ("utilities.powerball_predictor_core", "get_powerball_prediction"),
        "megamillions": ("utilities.mega_millions_predictor_core", "get_mega_millions_prediction"),
        "cash5": ("utilities.cash5_predictor_core", "get_cash5_prediction"),
        "pick3": ("utilities.pick3_predictor_core", "get_pick3_prediction"),
        "luckyforlife": ("utilities.lucky_for_life_predictor_core", "get_lucky_for_life_prediction"),
        "colorado": ("utilities.colorado_lottery_predictor_core", "get_colorado_lottery_prediction"),
    }
    try:
        import importlib
        mod, fn = mod_map[game]
        m = importlib.import_module(mod)
        f = getattr(m, fn)
        return f(root_dir=str(root), **kwargs)
    except Exception:
        return None

def _apply_coverage(game: str, sets: List[List[int]], n_sets: int, coverage_strength: float) -> List[List[int]]:
    # Bucket whites into hot/neutral/cold by frequency ranks; keep simple to avoid risk
    import pandas as pd
    # Use the first cache row ordering; approximate by rank of base frequency derived from recent window
    # We'll rebuild buckets inside smart_predict_v2 already; here just ensure we don't return near-duplicates
    if not sets: return sets
    # simple post-filter using diversity target proportional to coverage_strength
    target = 0.5 + 0.3 * max(0.0, min(1.0, float(coverage_strength)))
    return select_diverse(sets, n_sets, target=target)

def _predict_generic(game: str, root_dir: Optional[str], **kwargs):
    root = Path(root_dir or Path(__file__).resolve().parents[2])
    flags = _load_flags(root)
    use_smart = bool(_flag(flags, "enable_smart_v2", False))
    use_coverage = bool(_flag(flags, "enable_coverage_mode", False))
    diversity_target = float(_flag(flags, "diversity_target", 0.6))
    chaos_pct = float(_flag(flags, "chaos_pct", 0.05))
    # Oracle multiplier (light-touch)
    chaos_pct *= _oracle_multiplier(kwargs)
    n_sets = _n_sets(kwargs)

    # If smart not enabled, delegate to original core for zero-risk behavior
    if not use_smart:
        out = _delegate_original(game, root, **kwargs)
        if out is not None:
            return out

    # Smart v2 generation
    cache = _cache_path(root, game)
    df = _safe_read_csv(cache)

    # minimal model hook (models may be loaded elsewhere; keep None here for safety)
    model = None

    picks = predict_sets_v2(game, df, model, n_sets=n_sets, chaos_pct=chaos_pct, diversity_target=diversity_target)
    whites = [p["white"] for p in picks]
    specials = [ _clamp_special(game, p.get("special")) for p in picks ]

    if use_coverage and n_sets > 1:
        whites = _apply_coverage(game, whites, n_sets, float(_flag(flags, "coverage_strength", 0.5)))

    # package result like other backends: either dict for single or list for many
    if n_sets == 1:
        return {"white": whites[0], "special": specials[0]}
    else:
        return [{"white": w, "special": s} for w, s in zip(whites, specials)]

# Public API expected by predictor UIs
def get_powerball_prediction(root_dir: Optional[str] = None, **kwargs):
    return _predict_generic("powerball", root_dir, **kwargs)

def get_mega_millions_prediction(root_dir: Optional[str] = None, **kwargs):
    return _predict_generic("megamillions", root_dir, **kwargs)

def get_cash5_prediction(root_dir: Optional[str] = None, **kwargs):
    return _predict_generic("cash5", root_dir, **kwargs)

def get_pick3_prediction(root_dir: Optional[str] = None, **kwargs):
    return _predict_generic("pick3", root_dir, **kwargs)

def get_lucky_for_life_prediction(root_dir: Optional[str] = None, **kwargs):
    return _predict_generic("luckyforlife", root_dir, **kwargs)

def get_colorado_lottery_prediction(root_dir: Optional[str] = None, **kwargs):
    return _predict_generic("colorado", root_dir, **kwargs)
