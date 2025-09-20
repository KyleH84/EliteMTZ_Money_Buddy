from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


from pathlib import Path
from datetime import datetime, timedelta
from .config import data_dir, extras_dir
def ensure_dirs():
    for name in ["models","logs","quantum_hints","quantum_inbox"]:
        (data_dir()/name).mkdir(parents=True, exist_ok=True)
def ensure_secret():
    s = (extras_dir()/"future_secret.txt")
    if not s.exists():
        s.write_text("dev-secret-change-me\n", encoding="utf-8")
def maybe_autotrain():
    try:
        from ..training_engine import train
    except Exception:
        return
    stamp = data_dir()/ "logs"/"last_train.txt"
    if stamp.exists():
        # throttle: once per day
        try:
            t = datetime.fromisoformat(stamp.read_text(encoding="utf-8").strip())
            if (datetime.utcnow() - t) < timedelta(days=1):
                return
        except Exception:
            pass
    # Train lightweight models for all tabs (best-effort)
    for g in ["powerball","megamillions","cash5","pick3","luckyforlife","colorado"]:
        try:
            train(g)
        except Exception:
            pass
    stamp.write_text(datetime.utcnow().isoformat(), encoding="utf-8")

def bootstrap():
    ensure_dirs()
    ensure_secret()
    maybe_autotrain()
