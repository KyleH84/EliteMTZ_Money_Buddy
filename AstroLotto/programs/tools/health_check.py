from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Minimal health check wrapper to keep older admin pages working.
# Delegates to programs.features.health if available.
from typing import Dict, Any
try:
    from programs.features.health import scan_all as _scan_all
except Exception:
    _scan_all = None

def scan(root=None) -> Dict[str, Any]:
    if _scan_all is None:
        # Graceful fallback: nothing to report
        return {"ok": False, "note": "features.health not available", "checks": {}}
    try:
        return _scan_all(root)
    except Exception as e:
        return {"ok": False, "note": f"health scan failed: {e}", "checks": {}}
