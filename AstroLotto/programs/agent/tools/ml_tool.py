from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import pandas as pd, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from ._common import _load_game_df

FEATURES = {"lunar_phase","kp_3h_or_recent","kp_24h_max","ap_daily","f107_flux","flare_m72h","flare_x72h",
            "vix_close_or_spy20d","alignment_index","conjunction_rate","mercury_retro","dow","dom","woy","month","is_weekend"}

def ml_predictor(df_or_path=None, target_digit: int = 23) -> dict:
    df = _load_game_df(df_or_path)
    feat_cols = [c for c in df.columns if c in FEATURES]
    whites = [c for c in df.columns if str(c).lower().startswith(("n","w","white","ball"))]
    if not feat_cols: feat_cols = whites[:]
    if not feat_cols or not whites: return {"error":"no features or white columns"}
    X = df[feat_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).values
    y = (df[whites].apply(lambda r: target_digit in set(pd.to_numeric(r, errors='coerce').dropna().astype(int)), axis=1)).astype(int).values
    if len(X) < 50 or y.sum() == 0: return {"warning":"insufficient data"}
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1).fit(Xtr, ytr)
    auc = roc_auc_score(yte, clf.predict_proba(Xte)[:,1])
    return {"auc": float(auc), "feature_importances": {c: float(i) for c,i in zip(feat_cols, clf.feature_importances_)}}
