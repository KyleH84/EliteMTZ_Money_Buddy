from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/model_loader.py
from pathlib import Path
from typing import Optional, Any, Dict

def model_dir(game: str, head: str) -> Path:
    from os import environ as env
    base = Path(env.get("ASTRO_DATA_DIR","Data")) / "models" / game
    return base / f"{head}.ag"

def load_predictor(game: str, head: str):
    try:
        from autogluon.tabular import TabularPredictor
    except Exception:
        return None
    path = model_dir(game, head)
    if not path.exists():
        return None
    try:
        return TabularPredictor.load(str(path))
    except Exception:
        return None
