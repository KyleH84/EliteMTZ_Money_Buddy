# program/modules/services/explainers.py
from __future__ import annotations
from typing import Dict, List, Tuple, Any
import streamlit as st

def extract_metrics_from_row(row: Any) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Map a ranked-snapshot DataFrame row into pros/cons dicts expected by the explainer.
    The row is a pandas.Series-like object; missing keys are tolerated.
    """
    def _g(name: str, default=None):
        try:
            # try exact
            if name in row:
                return row[name]
        except Exception:
            pass
        # case-insensitive & with/without trailing colon
        lname = name.lower().rstrip(':')
        try:
            for k in getattr(row, 'index', []):
                if str(k).lower().rstrip(':') == lname:
                    return row[k]
        except Exception:
            # allow attribute access if it's a simple object
            return getattr(row, name, default)
        return default

    pros = {
        "Combined_with_agents": _g("Combined_with_agents"),
        "Combined": _g("Combined"),
        "RVOL": _g("RVOL"),
        "AgentBoost_exact": _g("AgentBoost_exact"),
    }
    cons = {
        "RelSPY": _g("RelSPY"),
        "P_up": _g("P_up"),
        "AgentBoost_exact": pros.get("AgentBoost_exact"),
        "RVOL": pros.get("RVOL"),
    }
    # numeric-cast when possible
    for d in (pros, cons):
        for k, v in list(d.items()):
            try:
                d[k] = float(v)
            except Exception:
                pass
    return pros, cons


def quick_reasoning(ticker: str, pros: Dict[str, float], cons: Dict[str, float]) -> Dict[str, List[str] | str]:
    """Plain-English explanation synthesized from common BreakoutBuddy metrics. Never empty."""
    def _get(d: Dict[str, float], key: str):
        # tolerate variant keys with colon/spacing/case
        for k, v in d.items():
            if str(k).lower().rstrip(':') == key.lower().rstrip(':'):
                return v
        return None

    rvol = _get(pros, "RVOL") if _get(pros, "RVOL") is not None else _get(cons, "RVOL")
    relspy = _get(cons, "RelSPY") if _get(cons, "RelSPY") is not None else _get(pros, "RelSPY")
    pup = _get(cons, "P_up") if _get(cons, "P_up") is not None else _get(pros, "P_up")
    agent_boost = _get(pros, "AgentBoost_exact") if _get(pros, "AgentBoost_exact") is not None else _get(cons, "AgentBoost_exact")

    bullets: List[str] = []

    # RVOL logic
    if isinstance(rvol, (int, float,)) and rvol == rvol:
        if rvol >= 1.5:
            bullets.append(f"Elevated relative volume (~{rvol:.2f}) suggests participation, not just drift.")
        elif rvol >= 1.1:
            bullets.append(f"Light volume expansion (~{rvol:.2f}); supportive but not decisive.")
        else:
            bullets.append(f"Subdued relative volume (~{rvol:.2f}); follow-through risk if no catalyst appears.")

    # Relative strength vs SPY
    if isinstance(relspy, (int, float,)) and relspy == relspy:
        if relspy > 0:
            bullets.append(f"Outperforming SPY on this window (RelSPY {relspy:.3f}).")
        elif relspy < 0:
            bullets.append(f"Underperforming SPY (RelSPY {relspy:.3f}); momentum may be fragile.")
        else:
            bullets.append("Neutral vs SPY; setup depends on stock-specific factors.")

    # Up-probability
    if isinstance(pup, (int, float,)) and pup == pup:
        if pup >= 0.6:
            bullets.append(f"Model tilt bullish (P_up {pup:.3f}); positive skew expected.")
        elif pup >= 0.5:
            bullets.append(f"Mild bullish bias (P_up {pup:.3f}); edge exists but is thin.")
        else:
            bullets.append(f"Sub-50% up-probability (P_up {pup:.3f}); better as watch-only until confirmation.")

    # Agent boost
    if isinstance(agent_boost, (int, float,)) and agent_boost == agent_boost:
        if agent_boost > 1.0:
            bullets.append(f"Agents boost confidence (x{agent_boost:.3f}).")
        elif agent_boost == 1.0:
            bullets.append("Agents neutral (no boost/penalty).")
        else:
            bullets.append(f"Agents penalize this setup (x{agent_boost:.3f}).")

    # Summary
    summary_bits: List[str] = []
    if isinstance(pup, (int, float,)) and pup == pup:
        if pup >= 0.6:
            summary_bits.append("Bullish bias with supportive stats.")
        elif pup >= 0.5:
            summary_bits.append("Slight bullish lean; confirm on price/volume.")
        else:
            summary_bits.append("Mixed/weak bias; better as a watch than a trade.")
    if isinstance(rvol, (int, float,)) and rvol == rvol and rvol >= 1.5:
        summary_bits.append("Volume expansion helps.")
    if isinstance(relspy, (int, float,)) and relspy == relspy and relspy < 0:
        summary_bits.append("Relative weakness is the drag.")

    if not summary_bits:
        summary_bits.append("Standard setup. No dominant factor either way.")

    return {
        "summary": " ".join(summary_bits),
        "details": bullets or ["Standard setup with neutral/conflicting signals; waiting for confirmation triggers."]
    }