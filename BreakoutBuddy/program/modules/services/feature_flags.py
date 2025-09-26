from __future__ import annotations
from pathlib import Path
import json, threading

# Project root = BreakoutBuddy/
PROJECT_DIR = Path(__file__).resolve().parents[3]
FLAGS_PATH = PROJECT_DIR / "Data" / "admin_flags.json"
_LOCK = threading.Lock()

_DEFAULTS = {
    "demo_mode": False,          # use neutral constants instead of live data
    "example_agents": False,     # route through example/placeholder agents
    "freeze_scores": False       # keep scores constant (screenshots/demos)
}

def _read():
    if FLAGS_PATH.exists():
        try:
            return json.loads(FLAGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return dict(_DEFAULTS)

def get_flags() -> dict:
    with _LOCK:
        data = _read()
        missing = {k: v for k, v in _DEFAULTS.items() if k not in data}
        if missing:
            data.update(missing)
            FLAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            FLAGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

def set_flags(**updates) -> dict:
    with _LOCK:
        data = _read()
        for k, v in updates.items():
            if k in _DEFAULTS:
                data[k] = bool(v)
        FLAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        FLAGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
