# utilities/feature_cache.py - Patch 4 (v1.0)
# Simple incremental feature caching to Parquet in Data/cache/.
from __future__ import annotations
import os
from pathlib import Path
from typing import Callable, Dict, Optional
import pandas as pd

def _data_root() -> Path:
    return Path(os.environ.get("ASTRO_DATA_DIR") or Path.cwd() / "Data")

def _cache_dir() -> Path:
    d = _data_root() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _date_col(df: pd.DataFrame) -> Optional[str]:
    for c in ("draw_date","date","Date"):
        if c in df.columns: return c
    return None

def cache_features(game: str, df: pd.DataFrame, build_fn: Callable[[pd.DataFrame, str], pd.DataFrame]) -> pd.DataFrame:
    game = (game or "").lower().strip()
    cache_path = _cache_dir() / f"features_{game}.parquet"

    dc = _date_col(df)
    if dc is None:
        return build_fn(df, game)

    if not cache_path.exists():
        feats = build_fn(df, game)
        try:
            feats.to_parquet(cache_path, index=False)
        except Exception:
            pass
        return feats

    try:
        old = pd.read_parquet(cache_path)
    except Exception:
        old = pd.DataFrame(columns=df.columns)

    dc_old = _date_col(old) or dc
    max_old = pd.to_datetime(old[dc_old]).max() if not old.empty else None

    if max_old is None:
        feats = build_fn(df, game)
        try: feats.to_parquet(cache_path, index=False)
        except Exception: pass
        return feats

    new_rows = df[pd.to_datetime(df[dc]) > max_old].copy()
    if new_rows.empty:
        return old

    new_feats = build_fn(new_rows, game)
    combined = pd.concat([old, new_feats], ignore_index=True)
    try:
        combined.to_parquet(cache_path, index=False)
    except Exception:
        pass
    return combined
