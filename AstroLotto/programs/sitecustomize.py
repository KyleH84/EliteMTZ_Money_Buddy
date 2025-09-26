from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/sitecustomize.py
import os, sys, time, random, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Data"
EXTRAS = ROOT / "Extras"
LOG = DATA / "logs"; LOG.mkdir(parents=True, exist_ok=True)

def _log(msg: str):
    try:
        with (LOG / "sitecustomize.log").open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass

# Pandas IO redirect: keep CSVs in Data/, but don't hijack absolute/URL paths
try:
    import pandas as _pd
    _orig_read_csv = _pd.read_csv
    _orig_to_csv = _pd.DataFrame.to_csv

    def _resolve_path(p):
        s = str(p)
        if "://" in s or os.path.isabs(s):
            return p
        # route typical app CSVs into Data
        if s.lower().endswith(".csv"):
            return str(DATA / s)
        return p

    def _read_csv(path, *a, **k):
        return _orig_read_csv(_resolve_path(path), *a, **k)

    def _to_csv(self, path, *a, **k):
        out = _resolve_path(path)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        return _orig_to_csv(self, out, *a, **k)

    _pd.read_csv = _read_csv
    _pd.DataFrame.to_csv = _to_csv
    _log("[OK] pandas IO redirect active")
except Exception as e:
    _log(f"[WARN] pandas patch failed: {e!r}")

# Ensemble patch: ensure models dir under Extras, and pre-create before training
try:
    import importlib as _importlib
    _orig_import = _importlib.import_module

    def _ensure_models_dir():
        d = EXTRAS / "models"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def import_module(name, package=None):
        m = _orig_import(name, package)
        if name in ("ensemble", "models.ensemble"):
            try:
                models_dir = _ensure_models_dir()
                # patch attribute MODEL_DIR or model_dir()
                if hasattr(m, "MODEL_DIR"):
                    setattr(m, "MODEL_DIR", str(models_dir))
                    _log("[OK] Patched ensemble.MODEL_DIR -> Extras/models")
                if hasattr(m, "model_dir"):
                    def _model_dir(*args, **kwargs):
                        return str(models_dir)
                    setattr(m, "model_dir", _model_dir)
                    _log("[OK] Patched ensemble.model_dir() -> Extras/models")
                # wrap train_auto to pre-create dir
                if hasattr(m, "train_auto"):
                    _train_auto = getattr(m, "train_auto")
                    def _wrapped_train_auto(*args, **kwargs):
                        _ensure_models_dir()
                        return _train_auto(*args, **kwargs)
                    setattr(m, "train_auto", _wrapped_train_auto)
                    _log("[OK] Wrapped ensemble.train_auto to ensure dir")
            except Exception as e:
                _log(f"[WARN] ensemble patch failed: {e!r}")
        return m

    _importlib.import_module = import_module
    # patch already-imported if any
    for _modname in ("ensemble","models.ensemble"):
        if _modname in sys.modules:
            import_module(_modname)
except Exception as e:
    _log(f"[WARN] import hook failed: {e!r}")
