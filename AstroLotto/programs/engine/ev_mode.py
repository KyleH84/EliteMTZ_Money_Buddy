from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# engine/ev_mode.py
from typing import List, Dict, Any, Tuple
import numpy as np

def popularity_risk_white(nums: List[int], white_max: int) -> float:
    if not nums: return 0.0
    nums = sorted(nums)
    risk = 0.0
    risk += 0.8 * sum(1 for n in nums if 1 <= n <= 31)
    risk += 0.5 * sum(1 for n in nums if n % 5 == 0)
    seq = sum(1 for i in range(1,len(nums)) if nums[i] == nums[i-1]+1)
    risk += 1.0 * seq
    dup = len(nums) - len(set(nums))
    risk += 2.0 * dup
    return float(risk) / float(len(nums) + 1e-6)

def adjust_for_ev(picks: List[Dict[str,Any]], white_probs: np.ndarray, white_max: int, max_drop_pct: float = 0.02) -> List[Dict[str,Any]]:
    out = []
    top = np.argsort(white_probs)[::-1] + 1
    for p in picks:
        ws = list(p.get("white", []))
        base_score = float(sum(white_probs[i-1] for i in ws))
        base_risk = popularity_risk_white(ws, white_max)
        best = (None, None, base_risk, base_score, ws)
        for i in range(len(ws)):
            for cand in top[:20]:
                if cand in ws: continue
                trial = ws.copy(); trial[i] = int(cand)
                if len(set(trial)) != len(trial): continue
                new_score = float(sum(white_probs[j-1] for j in trial))
                if new_score < base_score*(1.0-max_drop_pct): 
                    continue
                new_risk = popularity_risk_white(trial, white_max)
                if new_risk + 1e-9 < best[2] or (abs(new_risk-best[2])<1e-9 and new_score>best[3]):
                    best = (i, cand, new_risk, new_score, trial)
        ws2 = best[4]
        note = p.get("notes","")
        if ws2 != ws:
            note = (note + (" | " if note else "") + f"EV swap lowered risk {base_risk:.2f}→{best[2]:.2f}")
        out.append({"white": ws2, "special": p.get("special"), "notes": note})
    return out
