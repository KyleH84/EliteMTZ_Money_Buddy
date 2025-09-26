from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from typing import Dict, List, Tuple, Optional
import pandas as pd

def try_fit_probabilities(df: pd.DataFrame, game: str) -> Dict[int, float]:
    try:
        from sklearn.linear_model import LogisticRegression
    except Exception:
        return {}
    from collections import defaultdict
    whites = [c for c in df.columns if c.lower().startswith("white")]
    if not whites:
        return {}
    df = df.copy()
    if "draw_date" in df.columns:
        s = pd.to_datetime(df["draw_date"], errors="coerce")
        df["weekday"] = s.dt.weekday
    df["idx"] = range(len(df))
    out = defaultdict(list)
    for n in range(1, 71):
        y = (df[whites].apply(lambda row: int(n in set(pd.to_numeric(row, errors="coerce").dropna().astype(int))), axis=1)).values
        if y.sum() < 5:
            continue
        X = df[["idx","weekday"]] if "weekday" in df.columns else df[["idx"]]
        model = LogisticRegression(max_iter=500)
        model.fit(X, y)
        nextX = pd.DataFrame({"idx":[len(df)], "weekday":[(df["weekday"].iloc[-1]+1)%7 if "weekday" in df.columns else 0]})
        p = float(model.predict_proba(nextX)[0,1])
        out[n].append(p)
    return {k: sum(v)/len(v) for k,v in out.items() if v}
