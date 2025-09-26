from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/pmi.py
from typing import Dict, Tuple, List
import math
import pandas as pd

def pmi_pairs(df: pd.DataFrame, white_cols: List[str], top_k: int = 40) -> Dict[Tuple[int,int], float]:
    from collections import Counter
    if not white_cols:
        return {}
    rows = []
    for _, row in df.iterrows():
        try:
            nums = sorted([int(row[c]) for c in white_cols])
            rows.append(nums)
        except Exception:
            continue
    if not rows:
        return {}
    cnt_num = Counter(); cnt_pair = Counter()
    total_rows = len(rows)
    for nums in rows:
        s = set(nums)
        for n in s: cnt_num[n] += 1
        ln = len(nums)
        for i in range(ln):
            for j in range(i+1, ln):
                a,b = nums[i], nums[j]
                if a==b: continue
                cnt_pair[(a,b)] += 1
    out = {}; maxp = None
    for (a,b), c_ab in cnt_pair.items():
        p_ab = c_ab / total_rows
        p_a = cnt_num[a] / total_rows
        p_b = cnt_num[b] / total_rows
        if p_ab <= 0 or p_a <= 0 or p_b <= 0: continue
        pmi = math.log(p_ab) - math.log(p_a) - math.log(p_b)
        out[(a,b)] = pmi
        if maxp is None or pmi > maxp: maxp = pmi
    if not out or maxp is None or maxp <= 0: return {}
    for k in list(out.keys()): out[k] = max(0.0, out[k] / maxp)
    items = sorted(out.items(), key=lambda kv: -kv[1])[:top_k]
    return dict(items)