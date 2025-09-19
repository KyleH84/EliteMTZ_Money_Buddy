from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

def clip(x: float, lo: float = -1e9, hi: float = 1e9) -> float:
    try:
        return float(min(max(x, lo), hi))
    except Exception:
        return 0.0

def safe_float(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

@dataclass
class AgentResult:
    name: str
    score: float
    detail: Optional[str] = None
