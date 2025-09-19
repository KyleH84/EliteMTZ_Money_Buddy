# Minimal normalize_models wrapper for compatibility with older imports.
from __future__ import annotations
from typing import Dict, Any
try:
    from programs.utils.model_trainers import normalize_all as _normalize_all  # type: ignore
except Exception:
    _normalize_all = None

def normalize_models(root) -> Dict[str, Any]:
    if _normalize_all is None:
        return {"ok": False, "note": "model normalizer not available"}
    try:
        res = _normalize_all(root)
        return {"ok": True, "result": res}
    except Exception as e:
        return {"ok": False, "note": str(e)}
