
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import numpy as np
def sacred_weights(white_max, strength=0.05):
    w=np.ones(white_max,dtype=float); return w/w.sum()
