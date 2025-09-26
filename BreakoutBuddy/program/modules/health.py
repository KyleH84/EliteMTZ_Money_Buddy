from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from pathlib import Path
import json

def _program_root() -> Path:
    return Path(__file__).resolve().parents[1]

def _data_dir() -> Path:
    d = Path(__file__).resolve().parent / "Data"
    d.mkdir(parents=True, exist_ok=True)
    return d

def run_health_check() -> dict:
    root = _program_root()
    data_dir = _data_dir()
    out = {"ok": True, "checks": []}
    out["checks"].append({"name": "data_dir_exists", "path": str(data_dir), "ok": data_dir.exists()})
    out["ok"] = out["ok"] and data_dir.exists()
    csvs = list(data_dir.glob("*.csv"))
    out["checks"].append({"name": "csv_count", "count": len(csvs), "ok": len(csvs) > 0})
    out["ok"] = out["ok"] and (len(csvs) > 0)
    for mod in ["pandas", "yfinance"]:
        try:
            __import__(mod); ok = True
        except Exception:
            ok = False
        out["checks"].append({"name": f"import_{mod}", "ok": ok})
        if mod == "pandas":
            out["ok"] = out["ok"] and ok
    try:
        from modules import data as data_mod
        uni = data_mod.list_universe(5)
        out["checks"].append({"name": "list_universe", "count": len(uni), "ok": bool(uni)})
        out["ok"] = out["ok"] and bool(uni)
    except Exception as e:
        out["checks"].append({"name": "list_universe", "ok": False, "err": str(e)})
        out["ok"] = False
    return out
