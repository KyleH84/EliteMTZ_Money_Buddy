
from __future__ import annotations
from pathlib import Path
import json
from typing import List, Dict, Any
from .config import data_dir

def load_hint(game: str, draw_date: str) -> Dict[str, Any]:
    p = data_dir() / "quantum_hints" / game / f"{draw_date}.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def blend(game: str, draw_date: str, picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    hint = load_hint(game, draw_date)
    if not hint:
        return picks
    # If hint provides explicit numbers, prefer first hint and then keep the rest
    hb = hint.get("white"); hs = hint.get("special")
    if hb:
        picks = [{"white": hb, "special": hs}] + picks[1:]
    return picks
