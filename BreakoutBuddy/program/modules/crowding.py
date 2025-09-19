from __future__ import annotations
import pandas as pd
import numpy as np

def compute_crowd_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    near_high = (out["PctFrom200d"] > 0).astype(int)
    out["CrowdRisk"] = np.clip((out["RVOL"] - 1.0) * 0.7 + near_high * 0.6, 0, 3)
    out["RetailChaseRisk"] = np.clip((out["RSI2"] > 85).astype(int) * 1.0 + (out["RVOL"] > 1.5).astype(int) * 0.5, 0, 3)
    return out[["Ticker","CrowdRisk","RetailChaseRisk"]]
