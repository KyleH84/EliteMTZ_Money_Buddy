from __future__ import annotations
# Robust bridge so rom utilities import jackpots always resolves in Cloud or local.
# Tries normal package imports; if those fail, loads implementation by file path.

from pathlib import Path
import importlib, importlib.util

def _load():
    # 1) Try package imports
    for modname in (
        "AstroLotto.programs.utilities.jackpots",
        "BreakoutBuddy.program.utilities.jackpots",
    ):
        try:
            return importlib.import_module(modname)
        except Exception:
            pass

    # 2) Fallback: direct file-path load (Cloud-safe)
    root = Path(__file__).resolve().parent.parent
    candidates = [
        root / "AstroLotto"   / "programs" / "utilities" / "jackpots.py",
        root / "BreakoutBuddy" / "program"  / "utilities" / "jackpots.py",
    ]
    for c in candidates:
        if c.exists():
            spec = importlib.util.spec_from_file_location("__jackpots_impl__", c)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                return mod

    raise ModuleNotFoundError(
        "utilities.jackpots: implementation not found in AstroLotto/programs/utilities/ or BreakoutBuddy/program/utilities/"
    )

_impl = _load()
globals().update({k: getattr(_impl, k) for k in dir(_impl) if not k.startswith("_")})
