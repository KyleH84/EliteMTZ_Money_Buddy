from __future__ import annotations
# Robust bridge so `utilities.probability` always resolves.
# Tries AstroLotto then src/shared by package import; then falls back to direct file-path loading.
from pathlib import Path
import importlib, importlib.util

def _load():
    # Try normal package imports
    for modname in [
        "AstroLotto.programs.utilities.probability",
        "src.shared.utilities.probability",
    ]:
        try:
            return importlib.import_module(modname)
        except Exception:
            pass
    # File-path fallback
    root = Path(__file__).resolve().parent.parent
    candidates = [
        root / "AstroLotto" / "programs" / "utilities" / "probability.py",
        root / "src" / "shared" / "utilities" / "probability.py",
    ]
    for c in candidates:
        if c.exists():
            spec = importlib.util.spec_from_file_location("__probability_impl__", c)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                return mod
    raise ModuleNotFoundError("utilities.probability: no implementation found")

_impl = _load()
globals().update({k: getattr(_impl, k) for k in dir(_impl) if not k.startswith("_")})
