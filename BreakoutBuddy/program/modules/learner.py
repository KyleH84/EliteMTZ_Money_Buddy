from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import roc_auc_score
from sklearn.calibration import CalibratedClassifierCV

FEATURES = ["RSI2","RSI4","ConnorsRSI","PctFrom200d","RelSPY","RVOL","ATR","SqueezeHint","CrowdRisk","RetailChaseRisk"]

def train_online(df_hist: pd.DataFrame) -> Tuple[CalibratedClassifierCV, Dict[str,Any]]:
    df = df_hist.dropna(subset=FEATURES + ["label"]).copy()
    if df.empty:
        raise ValueError("No training rows")
    X = df[FEATURES].values
    y = df["label"].astype(int).values
    base = SGDClassifier(loss="log_loss", penalty="l2", alpha=1e-4, max_iter=2000, random_state=0)
    clf = CalibratedClassifierCV(base, method="sigmoid", cv=3)
    clf.fit(X, y)
    proba = clf.predict_proba(X)[:,1]
    auc = roc_auc_score(y, proba) if len(np.unique(y))>1 else 0.5
    meta = {"auc": float(auc), "n": int(len(df))}
    return clf, meta

def score_snapshot(model, snap_df: pd.DataFrame) -> pd.DataFrame:
    work = snap_df.copy()
    X = work[FEATURES].fillna(0).values
    prob = model.predict_proba(X)[:,1]
    work["P_up"] = prob
    return work
