from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import math

def _pct(x):
    try:
        return float(x) * 100.0
    except Exception:
        return 0.0

def _ratio_safe(a, b):
    try:
        a = float(a); b = float(b)
        return a / b if b not in (0, None) else 0.0
    except Exception:
        return 0.0

def make_ticker_advice(row, regime: dict | None = None) -> dict:
    """Return a dict with keys: headline, rating, pros, cons, context.
    Uses simple, interpretable rules from the available columns.
    """
    r = {k: row.get(k) for k in row.index} if hasattr(row, "index") else dict(row or {})
    pros, cons = [], []
    # Core signals
    rsi2 = float(r.get("RSI2", float("nan"))) if r.get("RSI2") is not None else float("nan")
    rsi4 = float(r.get("RSI4", float("nan"))) if r.get("RSI4") is not None else float("nan")
    crsi = float(r.get("ConnorsRSI", float("nan"))) if r.get("ConnorsRSI") is not None else float("nan")
    rel = float(r.get("RelSPY", 0.0) or 0.0)
    rvol = float(r.get("RVOL", 1.0) or 1.0)
    squeeze = float(r.get("SqueezeHint", 0.0) or 0.0)
    crowd = float(r.get("CrowdRisk", 0.0) or 0.0)
    chase = float(r.get("RetailChaseRisk", 0.0) or 0.0)
    p200 = float(r.get("PctFrom200d", 0.0) or 0.0)
    pup = float(r.get("P_up", 0.55) or 0.55)
    fscore = float(r.get("FinalScore", 0.0) or 0.0)
    close = float(r.get("Close", 0.0) or 0.0)
    atr = float(r.get("ATR", 0.0) or 0.0)
    chg = float(r.get("ChangePct", 0.0) or 0.0)

    # Pros
    if rsi2 < 5: pros.append("RSI2 extremely low (<5): bounce-friendly oversold")
    elif rsi2 < 10: pros.append("RSI2 low (<10): mild oversold tailwind")

    if rsi4 < 20: pros.append("RSI4 under 20: short-term weakness that often mean-reverts")

    if crsi < 25: pros.append("ConnorsRSI <25: composite oversold score")

    if rel > 0: pros.append("Outperforming SPY recently (RelSPY > 0)")

    if rvol >= 1.5: pros.append(f"Elevated volume (RVOL ≈ {rvol:.2f}) → attention/liquidity")
    elif rvol >= 1.1: pros.append(f"Slight volume uptick (RVOL ≈ {rvol:.2f})")

    if squeeze >= 0.5: pros.append("Squeeze/vol compression hint present")

    if chg <= -2.0: pros.append(f"Down {chg:.2f}% today: potential mean-reversion setup")

    if p200 >= 0: pros.append("Above 200‑day trend")

    # Cons
    if p200 <= -5: cons.append(f"{p200:.1f}% below 200‑day trend: fragile trend context")
    if rel < 0: cons.append("Underperforming SPY recently (RelSPY < 0)")
    if rsi2 > 80: cons.append("RSI2 very high (>80): overbought risk")
    if crowd > 1.5: cons.append(f"Crowded name (CrowdRisk ≈ {crowd:.2f})")
    if chase >= 0.7: cons.append(f"Retail chase risk high ({chase:.2f})")
    if _ratio_safe(atr, close) > 0.05: cons.append(f"Volatility high (ATR ≈ {atr/close*100:.1f}% of price)")

    # Simple star rating 1-5
    rp = 3.0  # start neutral
    if pup >= 0.60: rp += 0.5
    if pup >= 0.65: rp += 0.5
    if pup >= 0.70: rp += 0.5
    if fscore >= 0.08: rp += 0.5
    if fscore >= 0.12: rp += 0.5
    if rel > 0: rp += 0.25
    if p200 > 0: rp += 0.25
    rp -= 0.25 * max(0.0, crowd - 1.0)
    rp -= 0.25 * (1.0 if chase >= 0.7 else 0.0)
    if _ratio_safe(atr, close) > 0.06: rp -= 0.5
    rp = max(1.0, min(5.0, rp))
    rating = round(rp * 2) / 2.0  # half-stars

    # Headline / style
    style = []
    if rsi2 < 10: style.append("mean‑reversion bounce")
    if rel > 0 and p200 >= 0 and rsi2 < 50: style.append("pullback‑in‑uptrend")
    if squeeze >= 0.5: style.append("possible squeeze")
    if not style:
        style.append("standard setup")

    headline = f"{' / '.join(style).capitalize()} — {rating:.1f}★ | Model pop odds ≈ {pup:.0%} | Score {fscore:.3f}"

    context_bits = []
    if regime:
        try:
            tr = float(regime.get("spy20d_trend", 0.0))
            vol = float(regime.get("spy20d_vol", 0.0))
            slope = float(regime.get("ma200_slope5", 0.0))
            context_bits.append(f"SPY 20d trend {tr:+.2%}, vol {vol:.2%}, 200d slope {slope:+.3f}")
        except Exception:
            pass
    context = " | ".join(context_bits) if context_bits else ""

    return {
        "headline": headline,
        "rating": rating,
        "pros": pros,
        "cons": cons,
        "context": context,
    }
