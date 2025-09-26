from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

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
