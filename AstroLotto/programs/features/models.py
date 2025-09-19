
from __future__ import annotations
from pathlib import Path
from typing import Dict
from programs.features.refresh import refresh_all
# Import the model training helpers.  The ``programs.utils`` namespace is the
# canonical location for these modules in v14.5.  Older builds used a
# capitalised ``Program.utils`` alias, which is no longer present.
from programs.utils.model_trainers import train_all_for_game, GAMES  # type: ignore

def train_all(root: Path) -> Dict[str, dict]:
    out = {}
    for label in GAMES.keys():
        try:
            res = train_all_for_game(root, label)
            out[label] = res.models_trained
        except Exception as e:
            out[label] = {"error": str(e)}
    return out
