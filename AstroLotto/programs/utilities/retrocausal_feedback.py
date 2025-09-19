import numpy as np
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import datetime as dt
@dataclass
class RetroConfig:
    horizon_days:int=120
    memory:float=0.35
    data_dir:Path=Path("Data")
def apply_retro_weights(game, w, s, cfg=None):
    return w, s, {"horizon_days":120,"memory":0.35}
