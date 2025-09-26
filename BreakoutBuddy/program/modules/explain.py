from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from typing import Dict, Any
import math
def _risk_badge(row) -> str:
    try:
        rvol = float(row.get('RVOL', 1.0))
    except Exception:
        rvol = 1.0
    try:
        rsi = float(row.get('RSI4', 50.0))
    except Exception:
        rsi = 50.0
    heat = 0
    if rvol > 1.8: heat += 1
    if rsi > 70 or rsi < 30: heat += 1
    return '🔴 High' if heat >= 2 else ('🟡 Medium' if heat == 1 else '🟢 Low')
def _quick_list(row) -> str:
    pros, cons = [], []
    rel = float(row.get('RelSPY', 0.0) or 0.0)
    rvol = float(row.get('RVOL', 1.0) or 1.0)
    rsi = float(row.get('RSI4', 50.0) or 50.0)
    crsi = float(row.get('ConnorsRSI', 50.0) or 50.0)
    sq = float(row.get('SqueezeHint', 0.0) or 0.0)
    chg = float(row.get('ChangePct', 0.0) or 0.0)
    if rel > 0: pros.append('RelSPY+')
    if rvol > 1.2: pros.append('RVOL↑')
    if 45 <= rsi <= 60: pros.append('RSI ok')
    if sq > 0: pros.append('Squeeze?')
    if rel < 0: cons.append('RelSPY-')
    if rvol < 0.8: cons.append('Thin vol')
    if rsi >= 75: cons.append('Overbought')
    if rsi <= 25: cons.append('Oversold')
    if abs(chg) > 0.05: cons.append('Whippy')
    tags = ' | '.join(pros[:3] + cons[:3])
    return f"{row.get('Ticker','?')}: [{tags}] • Risk {_risk_badge(row).split()[0]}"

def _english_explanation(row: dict) -> str:
    # Robust, self-contained 2–5 sentence explanation using available fields.
    tkr = str(row.get('Ticker', '?'))
    rel = float((row.get('RelSPY', 0.0) or 0.0))
    rvol = float((row.get('RVOL', 1.0) or 1.0))
    rsi = float((row.get('RSI4', 50.0) or 50.0))
    crsi = float((row.get('ConnorsRSI', 50.0) or 50.0))
    chg = float((row.get('ChangePct', 0.0) or 0.0))
    atrp = float((row.get('ATRpct', row.get('ATR_Pct', 0.0)) or 0.0))
    sq = float((row.get('SqueezeHint', 0.0) or 0.0))
    sc = row.get('Combined', row.get('FinalScore', row.get('HeuristicScore', None)))

    parts = []

    # Sentence 1: context (relative strength + change + score)
    ctx_bits = []
    if rel > 0.02:
        ctx_bits.append("showing strength vs SPY")
    elif rel < -0.02:
        ctx_bits.append("lagging SPY")
    if chg:
        ctx_bits.append(f"today {('up' if chg>0 else 'down')} {abs(chg)*100:.1f}%")
    if sc is not None:
        try:
            sc_f = float(sc)
            ctx_bits.append(f"score {sc_f:.2f}")
        except Exception:
            pass
    ctx_txt = ", ".join(ctx_bits) if ctx_bits else "standard conditions"
    parts.append(f"{tkr} is under {ctx_txt}.")

    # Sentence 2: momentum (RSI/ConnorsRSI)
    if rsi >= 70:
        parts.append("Momentum looks extended; RSI is elevated and could fade.")
    elif rsi <= 30:
        parts.append("Momentum is washed out; RSI is low and may stabilize or continue weak.")
    elif 45 <= rsi <= 60:
        parts.append("Momentum is balanced; RSI sits in a neutral zone.")
    else:
        parts.append("Momentum is mixed; not clearly overbought or oversold.")
    if crsi:
        try:
            cr = float(crsi)
            if cr >= 70:
                parts[-1] += " ConnorsRSI also indicates a short-term stretch."
            elif cr <= 30:
                parts[-1] += " ConnorsRSI hints at short-term exhaustion."
        except Exception:
            pass

    # Sentence 3: participation/volume
    if rvol >= 1.8:
        parts.append("Participation is strong with RVOL well above average.")
    elif rvol >= 1.2:
        parts.append("Volume is above normal, indicating active interest.")
    elif rvol <= 0.8:
        parts.append("Volume is light; signals may be less reliable.")
    else:
        parts.append("Volume is near average.")

    # Sentence 4: volatility / structure
    if sq and sq > 0:
        parts.append("Range is compressing (squeeze), a break could travel quickly.")
    elif atrp and atrp >= 0.05:
        parts.append("Volatility is elevated; expect wider swings.")
    # else omit

    # Sentence 5: risk wrap using badge
    parts.append(f"Overall risk: {_risk_badge(row)}.")

    # Constrain to ~5 sentences max
    return " ".join(parts[:5]).strip()

def explain_for_row(row: dict, *, allow_local_llm: bool = False) -> Dict[str, Any]:
    quick = _quick_list(row)
    detailed = _english_explanation(row)
    badge = _risk_badge(row)
    if not allow_local_llm:
        return {'quick': quick, 'detailed': detailed, 'risk_badge': badge}
    try:
        from .services import local_llm
        if local_llm.is_available():
            feats = {
                'RelSPY': row.get('RelSPY', 0.0),
                'RVOL': row.get('RVOL', 1.0),
                'RSI4': row.get('RSI4', 50.0),
                'ConnorsRSI': row.get('ConnorsRSI', 50.0),
                'ChangePct': row.get('ChangePct', 0.0),
                'SqueezeHint': row.get('SqueezeHint', 0),
            }
            prompt = ('You are a trading assistant. Give a short, neutral explanation (2-4 sentences) '
                      'of intraday setup quality and risk for the following stock, based ONLY on these features. '
                      'Avoid jargon; keep it actionable.\n\n'
                      f"Ticker: {row.get('Ticker','?')}\n"
                      f"Features: {feats}\n")
            llm_text = local_llm.infer(prompt, max_tokens=140, temp=0.2)
            if llm_text:
                detailed = llm_text.strip()
                return {'quick': quick, 'detailed': detailed, 'risk_badge': badge}
    except Exception:
        pass
    return {'quick': quick, 'detailed': detailed, 'risk_badge': badge}
def explain_scan(df):
    rows = []
    for _, r in df.iterrows():
        d = explain_for_row(r.to_dict(), allow_local_llm=False)
        out = {k: r.get(k, None) for k in df.columns}
        out['QuickWhy'] = d['quick']
        out['RiskBadge'] = d['risk_badge']
        rows.append(out)
    try:
        import pandas as pd
        return pd.DataFrame(rows)
    except Exception:
        return rows
