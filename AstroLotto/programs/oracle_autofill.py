from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Oracle autofill wrapper: fills missing Markets/Space/Weird parts with live data
# and patches utilities.oracle_mode.compute_oracle at import time.
from typing import Dict, Any

try:
    from .oracle_live_feeds import get_live_parts, CAP_TOTAL
except Exception:
    def get_live_parts() -> Dict[str, float]:
        return {"markets": 0.0, "space": 0.0, "weird": 0.0, "cap": 0.33}
    CAP_TOTAL = 0.33

def _merge(base: Dict[str, Any]) -> Dict[str, Any]:
    parts = dict(base.get("parts", {}) or {})
    live = get_live_parts()
    for k in ("markets", "space", "weird"):
        if float(parts.get(k, 0.0) or 0.0) == 0.0:
            parts[k] = float(live.get(k, 0.0) or 0.0)
    moon = float(parts.get("moon", base.get("moon", 0.0)) or 0.0)
    total = float(parts.get("markets",0.0) + parts.get("space",0.0) + parts.get("weird",0.0) + moon)
    cap = float(live.get("cap", CAP_TOTAL) or CAP_TOTAL)
    base["parts"] = parts
    base["chaos"] = total if total <= cap else cap
    return base

def patch() -> bool:
    try:
        from . import oracle_mode as _oracle
    except Exception:
        return False
    orig = getattr(_oracle, "compute_oracle", None)
    if not callable(orig):
        return False
    def wrapped(date, lo, hi, settings, feeds):
        try:
            res = orig(date, lo, hi, settings, feeds) or {}
        except Exception:
            res = {"parts": {}}
        try:
            res = _merge(res)
        except Exception:
            pass
        return res
    setattr(_oracle, "compute_oracle", wrapped)
    return True

try:
    patch()
except Exception:
    pass
