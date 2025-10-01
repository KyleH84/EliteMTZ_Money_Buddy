from __future__ import annotations
from pathlib import Path
import json, os
from typing import List

APP_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("BREAKOUTBUDDY_DATA", APP_ROOT / "Data")).expanduser().resolve()
WATCHLIST_FILE = DATA_DIR / "watchlist.json"

def load_watchlist() -> List[str]:
    try:
        with WATCHLIST_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x).upper() for x in data]
    except Exception:
        pass
    return []

def save_watchlist(tickers: List[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tickers = sorted({str(t).upper() for t in tickers if t})
    tmp = WATCHLIST_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(tickers, f, indent=2)
    tmp.replace(WATCHLIST_FILE)
