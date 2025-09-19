
# utilities/model.py - v10.3.6 pluggable backends (LR/LGBM/XGB/CatBoost/AutoGluon)
from __future__ import annotations
from typing import Tuple, Optional, Any, Dict
import os
import numpy as np
import pandas as pd
import joblib
import uuid

# Scikit baseline
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV

# Optional backends (guarded imports)
try:
    from lightgbm import LGBMClassifier
except Exception:
    LGBMClassifier = None
try:
    from xgboost import XGBClassifier
except Exception:
    XGBClassifier = None
try:
    from catboost import CatBoostClassifier
except Exception:
    CatBoostClassifier = None
try:
    from autogluon.tabular import TabularPredictor
except Exception:
    TabularPredictor = None

def make_pipeline(backend: str = "lr"):
    backend = (backend or "lr").lower()
    if backend == "lightgbm" and LGBMClassifier is not None:
        return ("lightgbm", LGBMClassifier(
            n_estimators=500, learning_rate=0.05, max_depth=-1, subsample=0.9, colsample_bytree=0.9,
            objective="multiclass"
        ))
    if backend == "xgboost" and XGBClassifier is not None:
        return ("xgboost", XGBClassifier(
            n_estimators=600, learning_rate=0.05, max_depth=6, subsample=0.9, colsample_bytree=0.9,
            objective="multi:softprob", eval_metric="mlogloss", tree_method="hist"
        ))
    if backend == "catboost" and CatBoostClassifier is not None:
        return ("catboost", CatBoostClassifier(
            iterations=800, learning_rate=0.05, depth=8, loss_function="MultiClass", verbose=False
        ))
    if backend == "autogluon" and TabularPredictor is not None:
        return ("autogluon", None)  # handled in train_model
    # default LR
    pipe = Pipeline([
        ("scaler", StandardScaler(with_mean=True, with_std=True)),
        ("clf", LogisticRegression(multi_class="multinomial", solver="lbfgs", C=0.5, max_iter=2000))
    ])
    return ("lr", pipe)

def train_model(X: pd.DataFrame, y: pd.Series, backend: str = "lr", **kwargs):
    kind, model = make_pipeline(backend)
    if kind == "autogluon":
        if TabularPredictor is None:
            raise RuntimeError("AutoGluon not installed. Install autogluon.tabular to use this backend.")
        preset = kwargs.get("ag_preset", "best_quality")
        df = X.copy()
        df["y"] = y.values
        out_dir = kwargs.get("ag_out_dir") or os.path.join(".", "models", f"ag_{uuid.uuid4().hex[:8]}")
        os.makedirs(out_dir, exist_ok=True)
        pred = TabularPredictor(label="y", problem_type="multiclass", path=out_dir)
        pred.fit(df, presets=preset, verbosity=1)
        return ("autogluon", {"dir": out_dir, "preset": preset})
    if kind in ("lightgbm", "xgboost", "catboost"):
        model.fit(X.values, y.values)
        return (kind, model)
    # scikit pipeline
    model.fit(X.values, y.values)
    return (kind, model)

def calibrate_prefit(model_tuple, X_val: pd.DataFrame, y_val: pd.Series, method: str = "isotonic"):
    kind, model = model_tuple
    if kind == "autogluon":
        # AutoGluon already outputs calibrated-like probabilities; return as-is.
        return model_tuple
    # Wrap with CalibratedClassifierCV using prefit estimator
    calib = CalibratedClassifierCV(model, cv="prefit", method=method)
    calib.fit(X_val.values, y_val.values)
    return (kind, calib)

def predict_proba(model_tuple, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    kind, model = model_tuple
    if kind == "autogluon":
        if TabularPredictor is None:
            raise RuntimeError("AutoGluon not installed.")
        pred = TabularPredictor.load(model["dir"])
        proba_df = pred.predict_proba(X.copy())
        classes = np.array(list(proba_df.columns))
        proba = proba_df.values
        try:
            classes = classes.astype(int)
        except Exception:
            pass
        return classes, proba
    # scikit/GBMs
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X.values)
    else:
        proba = model.predict_proba(X)  # some wrappers accept DF
    if hasattr(model, "classes_"):
        classes = model.classes_
    elif hasattr(model, "named_steps"):
        classes = model.named_steps["clf"].classes_
    else:
        classes = np.arange(proba.shape[-1])
    return classes, proba

def save_model(model_tuple, path: str):
    joblib.dump(model_tuple, path)

def load_model(path: str):
    return joblib.load(path)
