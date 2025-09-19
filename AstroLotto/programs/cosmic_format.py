from __future__ import annotations
from typing import Dict, Any

def _pct(x: float) -> str:
    try:
        return f"{float(x)*100:.0f}%"
    except Exception:
        return "N/A"

def format_cosmic_conditions(data: Dict[str, Any]) -> str:
    if not isinstance(data, dict):
        return "Cosmic data unavailable."
    mp = data.get("moon_phase")
    mpos = data.get("moon_position") or {}
    retro = data.get("mercury_retrograde")
    align = data.get("alignment") or {}
    ad = align.get("details") or {}

    lines = []
    if mp is not None:
        lines.append(f"Moon phase: {_pct(mp)}")
    if isinstance(mpos, dict):
        s = mpos.get("summary") or ""
        lines.append(f"Moon position: {s}")
    if retro is not None:
        lines.append(f"Mercury retrograde: {'Yes' if retro else 'No'}")
    score = align.get("score")
    if score is not None:
        summary = ad.get("summary") or f"Score {score:.2f}"
        lines.append(f"Alignment: {summary}")
    return "\n".join(lines) if lines else "Cosmic data unavailable."
