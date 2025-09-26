
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import numpy as np, pandas as pd
def compute_per_position_probs(game, df):
    return {"white": [], "special": None}
