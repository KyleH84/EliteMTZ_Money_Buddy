
from __future__ import annotations
from typing import Optional, List
import re

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = True
except Exception:
    _VADER = False

try:
    import yfinance as yf
except Exception:
    yf = None  # optional

_POS = {"beat","beats","surge","surged","gain","gains","up","bull","bullish","positive","strong","record","growth","upgrade","outperform"}
_NEG = {"miss","misses","plunge","plunges","drop","drops","down","bear","bearish","negative","weak","cut","downgrade","underperform","loss"}

def _keyword_score(txt: str) -> float:
    t = txt.lower()
    pos = sum(1 for w in _POS if w in t); neg = sum(1 for w in _NEG if w in t)
    if pos == 0 and neg == 0: 
        return 0.0
    return max(-1.0, min(1.0, (pos - neg) / max(1.0, pos + neg)))

class SentimentAgent:
    """Light sentiment from recent Yahoo news. Optional; returns None on network errors."""

    def _fetch_titles(self, symbol: str) -> List[str]:
        if yf is None:
            return []
        try:
            t = yf.Ticker(symbol)
            items = getattr(t, "news", None)
            if not items:
                return []
            titles = []
            for it in items[:20]:
                title = it.get("title") or ""
                if title:
                    titles.append(title)
            return titles
        except Exception:
            return []

    def score(self, symbol: str) -> Optional[float]:
        titles = self._fetch_titles(symbol)
        if not titles:
            return None
        if _VADER:
            try:
                a = SentimentIntensityAnalyzer()
                vals = [a.polarity_scores(tt)["compound"] for tt in titles if tt]
                if not vals:
                    return None
                # average compound, map [-1..1] -> [-4..+4] (sentiment is smaller weight)
                return float(max(-4.0, min(4.0, sum(vals) / len(vals) * 4.0)))
            except Exception:
                pass
        # fallback: keyword heuristic
        vals = [_keyword_score(tt) for tt in titles if tt]
        if not vals:
            return None
        return float(max(-3.0, min(3.0, sum(vals) / len(vals) * 3.0)))
