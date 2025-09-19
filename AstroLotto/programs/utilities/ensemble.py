# Program/utilities/ensemble.py
"""
Shim for v11: provide train_auto / predict_auto expected by app_main.py,
delegating to Program/training_engine.py (train / predict).

This avoids missing legacy ensemble logic while keeping the new engine.
"""

from __future__ import annotations
from pathlib import Path
import sys

# Ensure Program/ is on sys.path so we can import training_engine cleanly
ROOT = Path(__file__).resolve().parents[2]  # project root
PROG = ROOT / "Program"
if str(PROG) not in sys.path:
    sys.path.insert(0, str(PROG))

try:
    # Our rebuilt engine exposes train(game) and predict(game, n_picks)
    from training_engine import train as _train_engine, predict as _predict_engine  # type: ignore
except Exception as e:
    # Fall back to names some older engines used
    _train_engine = None
    _predict_engine = None
    try:
        from training_engine import train_model as _train_engine  # type: ignore
    except Exception:
        pass
    try:
        from training_engine import predict_numbers as _predict_engine  # type: ignore
    except Exception:
        pass
    if _train_engine is None or _predict_engine is None:
        raise

def train_auto(game: str, cache_path=None, model_dir=None):
    """
    Auto-train wrapper used by the UI.
    Ignores cache_path/model_dir if the underlying engine manages paths itself.
    Returns the engine's training result dict.
    """
    return _train_engine(game)

def predict_auto(game: str, how_many: int = 3, model_dir=None):
    """
    Auto-predict wrapper used by the UI.
    Returns a list of predictions (dicts), consistent with training_engine.predict().
    """
    return _predict_engine(game, n_picks=how_many)
