from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import pandas as pd

def _num(s, col, default=0.0):
    if isinstance(s, pd.Series):
        return pd.to_numeric(s, errors="coerce").fillna(default)
    return default

def enrich_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add Combined_with_agents and AgentBoost_exact.
    Heuristic lift so UI works even without remote agents/keys.
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    s = df.copy()
    base = None
    for c in ("Combined_with_agents", "Combined", "Combined_base"):
        if c in s.columns:
            base = _num(s[c], c, 0.0)
            break
    if base is None:
        base = pd.Series(0.0, index=s.index)

    # Heuristic signals
    rsi = _num(s.get("RSI4", pd.Series(50.0, index=s.index)), "RSI4", 50.0)
    rel = _num(s.get("RelSPY", pd.Series(0.0, index=s.index)), "RelSPY", 0.0) * 100.0
    rvol = _num(s.get("RVOL", pd.Series(1.0, index=s.index)), "RVOL", 1.0) - 1.0
    sq = _num(s.get("SqueezeHint", pd.Series(0.0, index=s.index)), "SqueezeHint", 0.0)

    lift = (-0.05 * (rsi - 50.0)) + (0.20 * rel) + (1.0 * (10.0 * rvol)) + (2.0 * sq)
    lift = lift.clip(-20, 20)  # keep sane

    s["AgentBoost_exact"] = lift.round(2)
    s["Combined_with_agents"] = (base + lift).clip(lower=0.0, upper=100.0).round(2)
    return s

def run_agents_calibration(*, df: pd.DataFrame | None = None, lookback_days: int = 60, **kwargs):
    """No-op calibration that returns the heuristic weights we use above.
    Accepts **kwargs so older callers (e.g., limit_days) won't break.
    """
    return {
        "weights": {"RSI4": -0.05, "RelSPY": 0.20*100, "RVOL": 10.0, "SqueezeHint": 2.0},
        "lookback_days": lookback_days,
        "status": "ok-heuristic"
    }


def try_import_agents():
    """Return (has_agents: bool, Orchestrator: type|None, err: str|None)."""
    try:
        from modules.agents.orchestrator import AgentOrchestrator as Orchestrator
        return True, Orchestrator, None
    except Exception as e:
        return False, None, str(e)
