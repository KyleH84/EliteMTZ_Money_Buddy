from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


from datetime import datetime, timedelta
from typing import Optional, Dict, List

# Draw days based on Colorado-listed schedules (days-of-week only; time of day intentionally ignored):
# - Powerball: Monday, Wednesday, Saturday
# - Mega Millions: Tuesday, Friday
# - Colorado Lotto+: Wednesday, Saturday
# - Cash 5: Daily
# - Lucky for Life: Daily
# - Pick 3: Daily (Midday & Evening)
#
# We return the NEXT date (YYYY-MM-DD) on or after "now".

GAME_DOW: Dict[str, List[int]] = {
    "powerball": [0, 2, 5],       # Mon, Wed, Sat
    "megamillions": [1, 4],       # Tue, Fri
    "colorado": [2, 5],           # Wed, Sat (Colorado Lotto+)
    "cash5": list(range(7)),      # daily
    "luckyforlife": list(range(7)), # daily
    "pick3": list(range(7)),      # daily
}

def next_draw_date(game: str, now: Optional[datetime] = None) -> str:
    g = game.lower()
    days = GAME_DOW.get(g, list(range(7)))
    now = now or datetime.utcnow()
    wd = now.weekday()  # Mon=0..Sun=6
    for d in range(0, 8):
        cand = (wd + d) % 7
        if cand in days:
            return (now + timedelta(days=d)).date().isoformat()
    # fallback: tomorrow
    return (now + timedelta(days=1)).date().isoformat()
