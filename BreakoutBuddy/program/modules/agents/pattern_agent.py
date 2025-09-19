from __future__ import annotations
from typing import Mapping, Any
from .base import AgentResult, safe_float, clip

def compute(row: Mapping[str, Any]) -> AgentResult:
    o = safe_float(row.get("Open", 0.0))
    h = safe_float(row.get("High", 0.0))
    l = safe_float(row.get("Low", 0.0))
    c = safe_float(row.get("Close", 0.0))
    rng = ((h - l) / max(1e-6, abs(c) if c else (abs(o) if o else 1.0)))
    close_pos = 0.0
    if h > l + 1e-9:
        close_pos = (c - l) / (h - l)

    s = 0.0
    if rng >= 0.03 and close_pos >= 0.7:
        s += 2.0
    if rng >= 0.05 and c > o:
        s += 1.0
    if c < o and close_pos <= 0.3 and rng >= 0.03:
        s -= 1.5

    s = clip(s, -10.0, 10.0)
    detail = f"range%={rng*100:.1f}%, close_pos={close_pos:.2f}"
    return AgentResult(name="pattern", score=s, detail=detail)
