# Robust bridge so `from utilities import X` works inside AstroLotto.
# Resolution order:
#   1) local package: utilities.X  (this package)
#   2) absolute AL path: AstroLotto.programs.utilities.X
#   3) repo-root fallback: utilities.X (top-level package)
from __future__ import annotations
import importlib, sys

def __getattr__(name: str):
    candidates = [
        f"{__name__}.{name}",                      # local
        f"AstroLotto.programs.utilities.{name}",   # absolute AL
        f"utilities.{name}",                       # repo root fallback
    ]
    last_exc = None
    for modname in candidates:
        try:
            m = importlib.import_module(modname)
            # cache under this package so 'utilities.name' works
            sys.modules[f"{__name__}.{name}"] = m
            return m
        except Exception as e:
            last_exc = e
            continue
    raise ModuleNotFoundError(f"utilities.{name}: tried {candidates} but none were importable: {last_exc}")
