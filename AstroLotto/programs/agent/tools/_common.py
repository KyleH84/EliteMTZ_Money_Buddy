
from __future__ import annotations
from pathlib import Path
import pandas as pd

def _load_game_df(df_or_path=None) -> pd.DataFrame:
    if isinstance(df_or_path, pd.DataFrame):
        return df_or_path.copy()
    if df_or_path:
        p = Path(df_or_path)
        if p.exists(): return pd.read_csv(p)
    data = Path("Data")
    for name in ["cached_powerball_data.csv","cached_megamillions_data.csv","cached_cash5_data.csv",
                 "cached_luckyforlife_data.csv","cached_colorado_lottery_data.csv","cached_pick3_data.csv"]:
        f = data / name
        if f.exists(): return pd.read_csv(f)
    raise FileNotFoundError("No Data/*.csv found")
