
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
import math

from modules.agents.technical_agent import TechnicalAgent
from modules.agents.sentiment_agent import SentimentAgent

ProgressCB = Callable[[str, float], None]

@dataclass
class AgentReport:
    agent_rank: float           # -10..+10 combined
    notes: str                  # short summary
    components: Dict[str, float]  # per-agent scores
    ok: bool

def _safe(cb: Optional[ProgressCB], msg: str, p: float) -> None:
    try:
        if cb: cb(msg, max(0.0, min(1.0, float(p))))
    except Exception:
        pass

def _combine(scores: Dict[str, float]) -> float:
    if not scores:
        return 0.0
    # Simple robust combine: mean capped to [-10, 10]
    m = sum(scores.values()) / len(scores)
    return max(-10.0, min(10.0, m))

def run_for_symbols(symbols: List[str], progress_cb: Optional[ProgressCB] = None) -> Dict[str, AgentReport]:
    out: Dict[str, AgentReport] = {}
    ta = TechnicalAgent()
    sa = SentimentAgent()  # Works with or without VADER; network optional

    n = max(1, len(symbols))
    for i, sym in enumerate(symbols, start=1):
        _safe(progress_cb, f"Agents: {sym}", i / n * 0.95)
        scores: Dict[str, float] = {}
        notes_parts: List[str] = []
        ok = True

        try:
            s = ta.score(sym)
            if s is not None:
                scores["technical"] = float(s)
                notes_parts.append(f"Tech {s:+.1f}")
        except Exception as e:
            ok = False
            notes_parts.append(f"Tech err: {e}")

        try:
            s = sa.score(sym)
            if s is not None:
                scores["sentiment"] = float(s)
                notes_parts.append(f"Sent {s:+.1f}")
        except Exception as e:
            # Sentiment is optional; do not mark overall as failed
            notes_parts.append(f"Sent err: {e}")

        combined = _combine(scores)
        out[sym] = AgentReport(
            agent_rank=combined,
            notes=", ".join(notes_parts) if notes_parts else "No signals",
            components=scores,
            ok=ok,
        )

    _safe(progress_cb, "Agents: done", 1.0)
    return out
