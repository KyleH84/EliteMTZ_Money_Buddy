from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from typing import Dict, Any, List, Tuple
from pathlib import Path
import json
import pandas as pd
import numpy as np

from .registry import compute_all, list_agent_names

_WEIGHTS_FILE = "agent_weights.json"

def _data_dir() -> Path:
    here = Path(__file__).resolve()
    for up in [here, *here.parents]:
        cand = up / "Data"
        if cand.is_dir():
            return cand
        if up.name == "program":
            cand2 = up.parent / "Data"
            if cand2.is_dir():
                return cand2
    fb = here.parent / "Data"
    fb.mkdir(parents=True, exist_ok=True)
    return fb

def _weights_path() -> Path:
    return _data_dir() / _WEIGHTS_FILE

def _load_weights() -> Dict[str, float]:
    p = _weights_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_weights(w: Dict[str, float]) -> None:
    try:
        (_weights_path()).write_text(json.dumps(w, indent=2), encoding="utf-8")
    except Exception:
        pass

def get_current_weights(conn=None) -> pd.DataFrame:
    w = _load_weights()
    if not w:
        w = {name: 0.0 for name in list_agent_names()}
    return pd.DataFrame([{"agent": k, "weight": float(v)} for k,v in w.items()])

def agents_available() -> bool:
    return True

def _read_ranked_csv() -> pd.DataFrame:
    d = _data_dir()
    for name in ["ranked_latest.csv", "ranked.csv", "snapshot.csv"]:
        p = d / name
        if p.exists():
            try:
                return pd.read_csv(p)
            except Exception:
                pass
    return pd.DataFrame()

def _design_matrix(df: pd.DataFrame):
    rows = []
    for _, row in df.iterrows():
        sigs = compute_all(row.to_dict())
        rows.append([s.score for s in sigs])
    import numpy as np
    X = np.array(rows, dtype=float) if rows else np.zeros((0,0), dtype=float)
    names = list_agent_names()
    return X, names

def _target_vector(df: pd.DataFrame):
    import numpy as np
    if "Combined_base" in df.columns and pd.api.types.is_numeric_dtype(df["Combined_base"]):
        y = df["Combined_base"].astype(float).to_numpy()
    elif "Combined" in df.columns and pd.api.types.is_numeric_dtype(df["Combined"]):
        y = df["Combined"].astype(float).to_numpy()
    elif "P_up" in df.columns and pd.api.types.is_numeric_dtype(df["P_up"]):
        y = (df["P_up"].astype(float) * 100.0).to_numpy()
    else:
        y = np.zeros(len(df), dtype=float)
    return y

def run_agents_calibration(conn=None, lookback_days: int = 90, **kwargs) -> Dict[str, Any]:
    df = _read_ranked_csv()
    if df.empty or len(df) < 10:
        w = {name: 0.0 for name in list_agent_names()}
        save_weights(w)
        return {"status": "ok", "note": "Not enough data; saved zeros.", "weights": [{"agent":k,"weight":0.0} for k in w]}
    import numpy as np
    X, names = _design_matrix(df)
    y = _target_vector(df)
    if X.shape[0] != y.shape[0] or X.shape[0] == 0:
        w = {name: 0.0 for name in names}
        save_weights(w)
        return {"status": "ok", "note": "Calib input mismatch; saved zeros.", "weights": [{"agent":k,"weight":0.0} for k in w]}
    Xs = X.copy().astype(float)
    mu = Xs.mean(axis=0) if Xs.size else 0.0
    sd = Xs.std(axis=0) + 1e-6
    Xs = (Xs - mu) / sd
    lam = 1.0
    XtX = Xs.T @ Xs + lam * np.eye(Xs.shape[1])
    Xty = Xs.T @ y
    try:
        beta = np.linalg.solve(XtX, Xty)
    except Exception:
        beta = np.zeros(Xs.shape[1], dtype=float)
    w_raw = (beta / sd)
    l1 = float(np.sum(np.abs(w_raw))) + 1e-9
    scale = min(1.0, 4.0 / l1)
    w_scaled = w_raw * scale
    weights = {name: float(w) for name, w in zip(names, w_scaled)}
    save_weights(weights)
    return {
        "status": "ok",
        "lookback_days": int(lookback_days),
        "weights": [{"agent": n, "weight": float(weights[n])} for n in names],
        "note": "Calibrated ridge weights over latest ranked CSV.",
    }
