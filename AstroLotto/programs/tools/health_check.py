# Minimal health check wrapper to keep older admin pages working.
# Delegates to programs.features.health if available.
from __future__ import annotations
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
