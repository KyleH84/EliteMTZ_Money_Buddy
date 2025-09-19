from __future__ import annotations
from typing import Mapping, Any
from .base import AgentResult, safe_float, clip

def compute(row: Mapping[str, Any]) -> AgentResult:
    rv = safe_float(row.get("RVOL", 1.0), 1.0)
    rsi = safe_float(row.get("RSI4", 50.0), 50.0)
    rel = safe_float(row.get("RelSPY", 0.0), 0.0)
    chg = safe_float(row.get("ChangePct", 0.0), 0.0)
    sq  = str(row.get("SqueezeHint", "") or "").lower()

    s = 0.0
    if rv >= 2.0: s += 3.0
    elif rv >= 1.5: s += 2.0
    elif rv <= 0.8: s -= 1.0

    if rsi <= 20: s += 2.0
    elif rsi >= 80: s -= 2.0
    elif 45 <= rsi <= 65: s += 0.5

    if rel > 0: s += 1.0
    elif rel < 0: s -= 0.5

    if chg >= 0.03: s += 1.0
    elif chg <= -0.03: s -= 1.0

    if "squeeze" in sq: s += 0.5

    s = clip(s, -10.0, 10.0)
    detail = f"rv={rv:.2f}, rsi4={rsi:.1f}, relspy={rel:.3f}, chg={chg:.3f}"
    return AgentResult(name="technicals", score=s, detail=detail)
