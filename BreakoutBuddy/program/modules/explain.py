from __future__ import annotations

from typing import Dict, Any, Tuple, List
import math

# NOTE:
# This module is intentionally self-contained and defensive.
# It provides three public helpers used across the app:
#   - explain_for_row(row_dict) -> {quick, detailed, risk_badge}
#   - explain_scan(df) -> DataFrame with QuickWhy, RiskBadge
#   - explain_row(row)  (compat for ui/plain_english.py)
#
# It does NOT depend on Streamlit so it can be used in vectorized/batch paths.

# -----------------------------
# Small safe getters
# -----------------------------
def _f(row: Dict[str, Any], key: str, default: float) -> float:
    try:
        v = row.get(key, default)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return default
        return float(v)
    except Exception:
        return default

def _s(row: Dict[str, Any], key: str, default: str = "") -> str:
    try:
        v = row.get(key, default)
        if v is None:
            return default
        return str(v)
    except Exception:
        return default

# -----------------------------
# Badges & simple scoring
# -----------------------------
def _risk_badge(row: Dict[str, Any]) -> str:
    rvol  = _f(row, "RVOL", 1.0)       # relative volume (x)
    atrp  = _f(row, "ATRp", 2.0)       # ATR as % of price
    rsi4  = _f(row, "RSI4", 50.0)
    whips = abs(_f(row, "ChangePct", 0.0)) >= 5.0

    score = 0.0
    # base on volatility
    score += min(max((atrp - 1.5) / 2.5, 0.0), 1.0) * 0.45
    # add volume participation
    score += min(max((rvol - 1.0) / 2.0, 0.0), 1.0) * 0.35
    # RSI extremes add a bit of risk
    score += (1.0 if (rsi4 >= 75 or rsi4 <= 25) else 0.0) * 0.15
    # large daily change bumps risk
    score += (0.05 if whips else 0.0)

    if score < 0.35:
        return "Low • calmer tape"
    if score < 0.65:
        return "Med • active but manageable"
    return "High • fast tape / mind size"

def _pros_cons(row: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    pros: List[str] = []
    cons: List[str] = []

    rel   = _f(row, "RelSPY", 0.0)     # relative strength vs SPY
    rvol  = _f(row, "RVOL", 1.0)
    rsi4  = _f(row, "RSI4", 50.0)
    crsi  = _f(row, "ConnorsRSI", 50.0)
    chg   = _f(row, "ChangePct", 0.0)  # percent change today
    bbw   = _f(row, "BBWidth", 0.0)    # Bollinger width (%)

    # Pros
    if rel > 0.0:               pros.append("Outperforming SPY")
    if rvol >= 1.5:             pros.append("Heavier volume")
    if 45 <= rsi4 <= 60:        pros.append("Balanced RSI")
    if chg > 0:                 pros.append("Up on the day")
    if 0.0 < bbw < 8.0:         pros.append("Tight range / compression")

    # Cons
    if rel < 0.0:               cons.append("Lagging SPY")
    if rvol < 0.8:              cons.append("Thin participation")
    if rsi4 >= 75:              cons.append("Overbought")
    if rsi4 <= 25:              cons.append("Oversold")
    if abs(chg) >= 5.0:         cons.append("Whippy move")
    if bbw >= 12.0:             cons.append("Wide range / choppy")

    return pros, cons

def _english_explanation(row: Dict[str, Any]) -> str:
    tkr  = _s(row, "Ticker", "?")
    rel  = _f(row, "RelSPY", 0.0)
    rvol = _f(row, "RVOL", 1.0)
    rsi4 = _f(row, "RSI4", 50.0)
    crsi = _f(row, "ConnorsRSI", 50.0)
    chg  = _f(row, "ChangePct", 0.0)
    atrp = _f(row, "ATRp", 2.0)
    bbw  = _f(row, "BBWidth", 0.0)

    direction = "up" if chg >= 0 else "down"
    rel_str = "stronger than the market" if rel > 0 else ("weaker than the market" if rel < 0 else "inline with the market")

    bits = []
    bits.append(f"{tkr} is {direction} {abs(chg):.1f}% on the day and trading {rel_str}.")
    bits.append(f"Volume looks {'elevated' if rvol >= 1.5 else ('light' if rvol < 0.8 else 'normal')} (RVOL {rvol:.2f}).")
    if 45 <= rsi4 <= 60:
        bits.append(f"RSI(4) at {rsi4:.0f} is balanced; ConnorsRSI is {crsi:.0f}.")
    else:
        zone = 'overbought' if rsi4 >= 75 else ('oversold' if rsi4 <= 25 else 'neutral')
        bits.append(f"RSI(4) at {rsi4:.0f} sits in a {zone} zone; ConnorsRSI is {crsi:.0f}.")
    if bbw > 0:
        regime = "compressed" if bbw < 8 else ("expanding" if bbw < 12 else "wide")
        bits.append(f"Range looks {regime} (BB width ~{bbw:.1f}%).")
    bits.append(f"ATR is ~{atrp:.1f}% of price, so position sizing should respect a {('faster' if atrp >= 3 else 'moderate')} tape.")

    pros, cons = _pros_cons(row)
    if pros:
        bits.append("Pros: " + ", ".join(pros[:3]) + ".")
    if cons:
        bits.append("Cons: " + ", ".join(cons[:3]) + ".")

    return " ".join(bits)

# -----------------------------
# Public API
# -----------------------------
def explain_for_row(row: Dict[str, Any], allow_local_llm: bool = False) -> Dict[str, str]:
    # Plain, deterministic output. If an LLM is later wired, we still fall back safely.
    quick = ""
    detailed = ""
    try:
        pros, cons = _pros_cons(row)
        pro_str = " | ".join(pros[:3]) if pros else "Standard setup"
        con_str = " | ".join(cons[:3]) if cons else ""
        quick = f"{_s(row, 'Ticker', '?')}: {pro_str}" + (f" • {con_str}" if con_str else "")
    except Exception:
        quick = f"{_s(row, 'Ticker', '?')}: Standard setup"

    try:
        detailed = _english_explanation(row)
    except Exception:
        detailed = quick

    badge = _risk_badge(row)
    return {"quick": quick, "detailed": detailed, "risk_badge": badge}

def explain_scan(df):
    rows = []
    # Avoid importing pandas at module import to keep this file lightweight.
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return df

    if df is None or getattr(df, "empty", True):
        return df

    for _, r in df.iterrows():
        d = explain_for_row(r.to_dict(), allow_local_llm=False)
        out = {k: r.get(k, None) for k in df.columns}
        out["QuickWhy"] = d["quick"]
        out["RiskBadge"] = d["risk_badge"]
        rows.append(out)

    try:
        return pd.DataFrame(rows)
    except Exception:
        return rows

# Compatibility for ui/plain_english.py
def explain_row(row: Any) -> str:
    try:
        # Support both dict-like and pandas Series
        rd = row if isinstance(row, dict) else getattr(row, "to_dict", lambda: {})()
        return explain_for_row(rd)["detailed"]
    except Exception:
        return ""
