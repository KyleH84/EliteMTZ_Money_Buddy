from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from typing import Mapping, Any
from .base import AgentResult, safe_float, clip

def compute(row: Mapping[str, Any]) -> AgentResult:
    h = safe_float(row.get("High", 0.0))
    l = safe_float(row.get("Low", 0.0))
    c = safe_float(row.get("Close", 0.0))
    rv = safe_float(row.get("RVOL", 1.0))
    rng = (h - l) / max(1e-6, abs(c) if c else 1.0)
    score = 0.0
    if rng >= 0.06: score -= 2.0
    elif rng >= 0.04: score -= 1.0
    if rv <= 0.6: score -= 1.0
    score = clip(score, -10.0, 10.0)
    return AgentResult(name="volatility", score=score, detail=f"range%={rng*100:.1f}%, rvol={rv:.2f}")
