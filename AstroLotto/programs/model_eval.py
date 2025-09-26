from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


# programs/utils/model_eval.py — Minimal safe evaluator for Admin Models tab
from pathlib import Path
from typing import Dict, Any

def _cache_path(root: Path, game: str) -> Path:
    names = {
        "powerball": "cached_powerball_data.csv",
        "megamillions": "cached_megamillions_data.csv",
        "cash5": "cached_cash5_data.csv",
        "pick3": "cached_pick3_data.csv",
        "luckyforlife": "cached_luckyforlife_data.csv",
        "colorado": "cached_colorado_lottery_data.csv",
    }
    return root / "Data" / names[game]

def evaluate_game(root: Path, game: str) -> Dict[str, Any]:
    """Return a small status dict for Admin display.
    Avoids heavy computation; just reports cache rows and if a model file exists.
    """
    import pandas as pd, json
    cache = _cache_path(root, game)
    rows = 0
    if cache.exists():
        try:
            df = pd.read_csv(cache)
            rows = len(df)
        except Exception:
            rows = 0
    model_path = root / "Data" / "models" / f"{game}_model.json"
    models = []
    if model_path.exists():
        try:
            meta = json.loads(model_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {"path": str(model_path)}
        models.append(meta)
    return {"cache_exists": cache.exists(), "cache_draws": rows, "models": models}
