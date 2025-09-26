from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


# utilities/eval.py - v10.3 walk-forward metrics
import numpy as np
import pandas as pd
from typing import Dict, Any
from .model import make_pipeline

def walk_forward(X: pd.DataFrame, y: pd.Series, train_min: int = 400, step: int = 1) -> Dict[str, Any]:
    n = len(X)
    if n < train_min + 5:
        return {"n": n, "ok": False, "reason": "not_enough_data"}
    probs = []
    truths = []
    classes_ref = None
    for i in range(train_min, n, step):
        Xtr, ytr = X.iloc[:i], y.iloc[:i]
        Xt, yt = X.iloc[[i]], y.iloc[i]
        _, model = make_pipeline("lr")  # for evaluation baseline we can use LR; you can extend to chosen backend
        model.fit(Xtr.values, ytr.values)
        proba = model.predict_proba(Xt.values)[0]
        classes = model.named_steps["clf"].classes_
        if classes_ref is None:
            classes_ref = classes
        else:
            aligned = np.zeros_like(proba, dtype=float)
            for j, c in enumerate(classes):
                k = np.where(classes_ref == c)[0][0]
                aligned[k] = proba[j]
            proba = aligned
        probs.append(proba)
        truths.append(int(yt))
    probs = np.array(probs)
    truths = np.array(truths)
    class_to_idx = {c:i for i,c in enumerate(classes_ref)}
    y_idx = np.array([class_to_idx[t] for t in truths])
    ll = float(np.mean([-np.log(max(1e-12, probs[i, y_idx[i]])) for i in range(len(y_idx))]))
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(y_idx)), y_idx] = 1.0
    brier = float(np.mean(np.sum((probs - onehot)**2, axis=1)))
    topk = 5
    hits = 0
    for i in range(len(y_idx)):
        topk_idx = np.argsort(probs[i])[::-1][:topk]
        if y_idx[i] in topk_idx:
            hits += 1
    hit_rate = hits / len(y_idx)
    return {"n": int(n), "ok": True, "classes": [int(c) for c in classes_ref], "logloss": ll, "brier": brier, "top5_hit": hit_rate}
