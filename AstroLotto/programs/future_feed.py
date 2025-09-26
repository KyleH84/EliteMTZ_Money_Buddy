from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


from pathlib import Path
import json, hmac, hashlib
from typing import Optional
from .config import data_dir, extras_dir

def _secret() -> bytes:
    s = (extras_dir() / "future_secret.txt")
    if not s.exists():
        s.write_text("dev-secret-change-me\n", encoding="utf-8")
    return s.read_text(encoding="utf-8").strip().encode()

def _hints_dir(game: str) -> Path:
    p = data_dir() / "quantum_hints" / game
    p.mkdir(parents=True, exist_ok=True)
    return p

def _inbox_dir(game: str) -> Path:
    p = data_dir() / "quantum_inbox" / game
    p.mkdir(parents=True, exist_ok=True)
    return p

def _verify(payload: dict, sig_hex: str) -> bool:
    key = _secret()
    msg = json.dumps(payload, sort_keys=True).encode()
    want = hmac.new(key, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(want, sig_hex)

def promote_if_valid(game: str, draw_date: str) -> bool:
    inbox = _inbox_dir(game) / f"{draw_date}.envelope.json"
    if not inbox.exists():
        return False
    try:
        env = json.loads(inbox.read_text(encoding="utf-8"))
        payload = env.get("payload", {})
        sig = env.get("sig", "")
        if not _verify(payload, sig):
            return False
        # write hint
        out = _hints_dir(game) / f"{draw_date}.json"
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False
