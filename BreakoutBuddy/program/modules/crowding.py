from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import pandas as pd
import numpy as np

def compute_crowd_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    near_high = (out["PctFrom200d"] > 0).astype(int)
    out["CrowdRisk"] = np.clip((out["RVOL"] - 1.0) * 0.7 + near_high * 0.6, 0, 3)
    out["RetailChaseRisk"] = np.clip((out["RSI2"] > 85).astype(int) * 1.0 + (out["RVOL"] > 1.5).astype(int) * 0.5, 0, 3)
    return out[["Ticker","CrowdRisk","RetailChaseRisk"]]
