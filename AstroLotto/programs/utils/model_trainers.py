
# programs/utils/model_trainers.py — route Admin Train buttons to the trainer + normalize
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

GAMES = ("powerball","megamillions","cash5","pick3","luckyforlife","colorado")

def _normalize_one(root: Path, game: str) -> None:
    try:
        from programs.tools.normalize_models import normalize_models
        reports = normalize_models(str(root))
        # keep silent; this is a safeguard after train
    except Exception:
        pass

def train_all_for_game(root: Path, game: str) -> Dict[str, Any]:
    if game not in GAMES:
        return {"ok": False, "note": "unknown game"}
    try:
        from programs.training_engine import train_frequency_model
    except Exception as e:
        return {"ok": False, "note": f"training engine not available: {e}"}
    res = train_frequency_model(game)
    _normalize_one(root, game)
    return res
