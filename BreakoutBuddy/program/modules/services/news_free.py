from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


from typing import List
try:
    import yfinance as yf
except Exception:
    yf = None

def get_titles(symbol: str, limit: int = 20) -> List[str]:
    """Free helper: fetch recent news titles from yfinance (best-effort, optional)."""
    if yf is None:
        return []
    try:
        t = yf.Ticker(symbol)
        items = getattr(t, "news", None) or []
        out = []
        for it in items[:max(1, int(limit))]:
            title = it.get("title") or ""
            if title:
                out.append(title)
        return out
    except Exception:
        return []
