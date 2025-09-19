
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import importlib, inspect

def _resolve_backend(candidates: List[Tuple[str,str]]):
    for modname, funcname in candidates:
        try:
            m = importlib.import_module(modname)
            f = getattr(m, funcname, None)
            if callable(f):
                return f, f"{modname}.{funcname}"
        except Exception:
            continue
    return None, None

def _normalize_one(obj) -> Optional[Dict[str, Any]]:
    try:
        if isinstance(obj, dict):
            if "white" in obj and "special" in obj:
                whites = obj.get("white") or []
                special = obj.get("special")
                if isinstance(special, list):
                    special = (special[0] if special else None)
                special = (int(special) if special is not None else None)
                return {"white": list(map(int, whites)), "special": special}
            if "numbers" in obj:
                nums = list(map(int, obj["numbers"]))
                return {"white": nums[:5], "special": (nums[5] if len(nums)>5 else None)}
        if isinstance(obj, list):
            return {"white": list(map(int, obj)), "special": None}
    except Exception:
        return None
    return None

def _normalize_predictions(result) -> List[Dict[str, Any]]:
    if result is None:
        return []
    out: List[Dict[str, Any]] = []
    if isinstance(result, list):
        for item in result:
            norm = _normalize_one(item)
            if norm: out.append(norm)
    else:
        norm = _normalize_one(result)
        if norm: out.append(norm)
    return out

def _best_effort_call(f, root_dir: Optional[str], **kwargs):
    try:
        sig = inspect.signature(f)
        if "root_dir" in sig.parameters:
            return f(root_dir=root_dir, **kwargs)
    except Exception:
        pass
    try:
        return f(root_dir, **kwargs)
    except TypeError:
        return f(**kwargs)
