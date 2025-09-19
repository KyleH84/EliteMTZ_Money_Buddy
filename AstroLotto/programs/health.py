
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import pandas as pd

@dataclass
class CacheHealth:
    game: str
    path: Path
    exists: bool
    size_bytes: int
    rows: int
    note: Optional[str] = None

GAME_TO_CACHE = {
    "Mega Millions": "cached_megamillions_data.csv",
    "Powerball": "cached_powerball_data.csv",
    "Colorado Cash 5": "cached_cash5_data.csv",
    "Lucky for Life": "cached_luckyforlife_data.csv",
    "Colorado Lotto+": "cached_colorado_lottery_data.csv",
    "Pick 3": "cached_pick3_data.csv",
}

def project_root_from_page(file_path: str) -> Path:
    p = Path(file_path).resolve()
    return p.parent.parent.parent  # .../programs/pages/<file>.py -> root

def _cache_path(root: Path, fname: str) -> Path:
    return root / "Data" / fname

def check_one(root: Path, game: str) -> CacheHealth:
    fname = GAME_TO_CACHE[game]
    p = _cache_path(root, fname)
    if not p.exists():
        return CacheHealth(game, p, False, 0, 0, "missing")
    size = p.stat().st_size
    if size == 0:
        return CacheHealth(game, p, True, 0, 0, "empty file")
    try:
        df = pd.read_csv(p)
        return CacheHealth(game, p, True, size, len(df), None if len(df)>0 else "no rows")
    except Exception as e:
        return CacheHealth(game, p, True, size, 0, f"unreadable: {e}")

def delete_if_empty(p: Path) -> bool:
    try:
        if p.exists() and p.stat().st_size == 0:
            p.unlink()
            return True
    except Exception:
        pass
    return False
