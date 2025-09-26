
from __future__ import annotations
import datetime as _dt
import json, re
from dataclasses import dataclass
from typing import List, Optional
import requests

@dataclass
class DrawResult:
    game: str
    draw_epoch: int
    white_winning: List[int]
    special_winning: Optional[int] = None

class ResultsProvider:
    """Providers for official draw results."""
    def fetch_powerball_recent(self, count: int = 50) -> List[DrawResult]:
        url = f"https://www.powerball.com/api/v1/numbers/powerball/recent{count}?format=json"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        out: List[DrawResult] = []
        for row in data:
            try:
                date_str = row.get("draw_date")
                dt = _dt.datetime.strptime(date_str, "%Y-%m-%d").replace(hour=22, minute=0, second=0, microsecond=0)
                epoch = int(dt.timestamp())
                whites = [int(x) for x in re.split(r"[\s,]+", row["field_winning_numbers"].strip()) if x]
                special = int(row.get("field_winning_numbers_special") or 0) or None
                out.append(DrawResult(game="powerball", draw_epoch=epoch, white_winning=whites, special_winning=special))
            except Exception:
                continue
        return out
