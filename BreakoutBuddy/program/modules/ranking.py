from __future__ import annotations
import numpy as np
import pandas as pd

def _ensure_col(df: pd.DataFrame, name: str, default: float = 0.0) -> pd.Series:
    if name not in df.columns:
        df[name] = default
    return pd.to_numeric(df[name], errors="coerce").fillna(default)

def blended_ranking(df: pd.DataFrame, regime: dict | None = None, top_n: int = 50) -> pd.DataFrame:
    """Rank ideas using a simple, robust blend that tolerates missing columns."""
    work = df.copy()

    # Required/safe columns
    p_up = _ensure_col(work, "P_up", 0.55).clip(0.0, 1.0)
    crowd = _ensure_col(work, "CrowdRisk", 0.0).clip(lower=0.0)
    retail = _ensure_col(work, "RetailChaseRisk", 0.0).clip(lower=0.0)
    squeeze = _ensure_col(work, "SqueezeHint", 0.0).clip(lower=0.0, upper=1.0)

    # Regime multiplier (bounded)
    regime = regime or {}
    trend = float(regime.get("spy20d_trend") or 0.0)
    slope = float(regime.get("ma200_slope5") or 0.0)
    vol = float(regime.get("spy20d_vol") or 0.0)
    regime_mult = 1.0 + max(trend, 0.0) * 0.5 + max(slope, 0.0) * 0.05 - min(max(vol, 0.0), 0.05) * 0.5
    regime_mult = float(np.clip(regime_mult, 0.7, 1.3))

    # Crowd penalty (bounded)
    crowd_pen = 1.0 - (crowd / 20.0) - (retail / 30.0)
    crowd_pen = crowd_pen.clip(lower=0.5, upper=1.0)

    # Optional Agents overlays
    agents_score = _ensure_col(work, "AgentsScore", np.nan)
    agents_conf  = _ensure_col(work, "AgentsConf", np.nan)

    # Build a bounded multiplier if agent columns exist
    agents_mult = pd.Series(1.0, index=work.index)
    has_agents = agents_score.notna() & agents_conf.notna()
    if has_agents.any():
        # Centered around 1.0: +10% at score=1, -10% at score=0, scaled by confidence
        bump = ((agents_score.clip(0.0, 1.0) - 0.5) * 0.20) * agents_conf.clip(0.0, 1.0)
        agents_mult = (1.0 + bump).clip(0.85, 1.15)
        agents_mult = agents_mult.where(has_agents, 1.0)

    # Final score
    work["FinalScore"] = p_up * regime_mult * crowd_pen * (1.0 + 0.05 * squeeze) * agents_mult
    # Derive exact agent lift components
    try:
        base = work["FinalScore"] / agents_mult.replace(0, 1.0)
        work["Combined_base"] = base
        work["Combined_with_agents"] = work["FinalScore"]
        work["AgentBoost_exact"] = work["Combined_with_agents"] - work["Combined_base"]
        if "Combined" not in work.columns:
            work["Combined"] = work["Combined_with_agents"]
    except Exception:
        work["Combined_base"] = work.get("FinalScore", 0.0)
        work["Combined_with_agents"] = work.get("FinalScore", 0.0)
        work["AgentBoost_exact"] = 0.0

    work = work.sort_values("FinalScore", ascending=False)
    return work.head(top_n if top_n and top_n > 0 else len(work))
