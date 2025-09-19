
from __future__ import annotations

def safe_float(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default
