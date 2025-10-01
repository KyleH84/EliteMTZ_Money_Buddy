from __future__ import annotations
# program/modules/agents/auto_tune.py

import os, json
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

import pandas as pd  # type: ignore
from pathlib import Path
import streamlit as st

# Resolve app root and Data dir (env/session override friendly if app sets BREAKOUTBUDDY_DATA)
APP_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("BREAKOUTBUDDY_DATA", APP_ROOT / "Data")).expanduser().resolve()

AGENTS_DIR = DATA_DIR / "agents"
AGENTS_DIR.mkdir(parents=True, exist_ok=True)
WEIGHTS_PATH = AGENTS_DIR / "weights.json"


DEFAULT_AGENTS = ["tech", "pattern", "volatility"]


def _load_candidate_frames() -> List[pd.DataFrame]:
    """Collect candidate CSVs with training signals from the Data folder.
    Tries common file names; degrades to scanning *.csv and filtering by columns.
    """
    candidates: List[pd.DataFrame] = []

    # Preferred names
    names = [
        "ranked_latest.csv",
        "ranked.csv",
        "explore_snapshot_latest.csv",
        "snapshot_latest.csv",
        "watchlist_snapshot_latest.csv",
    ]
    for nm in names:
        p = DATA_DIR / nm
        if p.exists():
            try:
                df = pd.read_csv(p)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    candidates.append(df)
            except Exception:
                pass

    # If nothing yet, scan *.csv
    if not candidates:
        try:
            for p in DATA_DIR.glob("*.csv"):
                try:
                    df = pd.read_csv(p)
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        candidates.append(df)
                except Exception:
                    continue
        except Exception:
            pass
    return candidates


def _select_training_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
    """Return features (agents) and a target series if present.
    Target priority: 'FutureRet', then 'ChangePct', then next-day derived (not attempted here).
    """
    lower = {c.lower(): c for c in df.columns}
    # Features: any columns that look like agent scores
    feat_keys = []
    for k in list(lower.keys()):
        if any(token in k for token in ("agent", "tech", "pattern", "volatility")):
            feat_keys.append(lower[k])
    # If not found, try the canonical names
    for k in DEFAULT_AGENTS:
        if k in lower and lower[k] not in feat_keys:
            feat_keys.append(lower[k])

    X = df[feat_keys] if feat_keys else pd.DataFrame()

    # Target column
    y = None
    for t in ("futureret", "future_ret", "next_ret", "next_return", "changepct", "change_pct"):
        if t in lower:
            y = df[lower[t]]
            break

    return X, y


def _normalize_weights(w: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, float(v)) for v in w.values())
    if total <= 1e-9:
        # equal weights
        n = len(w) if w else 0
        if n == 0:
            return {}
        eq = 1.0 / n
        return {k: eq for k in w.keys()}
    return {k: max(0.0, float(v)) / total for k, v in w.items()}


def _save_weights_json(weights: Dict[str, float], meta: Dict[str, str]) -> None:
    WEIGHTS_PATH.write_text(json.dumps({"weights": weights, "meta": meta}, indent=2), encoding="utf-8")


@st.cache_data(ttl=900, show_spinner=False)
def get_current_weights() -> pd.DataFrame:
    """Return a small DataFrame with agent weights. If none saved, return equal weights."""
    if WEIGHTS_PATH.exists():
        try:
            obj = json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))
            w = obj.get("weights", {})
            if isinstance(w, dict) and w:
                return pd.DataFrame({"agent": list(w.keys()), "weight": [float(v) for v in w.values()]})
        except Exception:
            pass
    # Default equal weights across DEFAULT_AGENTS
    eq = _normalize_weights({k: 1.0 for k in DEFAULT_AGENTS})
    return pd.DataFrame({"agent": list(eq.keys()), "weight": list(eq.values())})


def run_agents_calibration(lookback_days: int = 90) -> Dict[str, object]:
    """Estimate weights from available CSVs. Never returns all-zero weights.
    Strategy:
      1) Try to find features that look like agent scores and a target column (FutureRet/ChangePct).
      2) If target exists: use absolute Spearman correlation as importance.
      3) If no target: fall back to variance/dispersion of each agent feature (avoid dead/constant signals).
      4) Normalize; if empty, return equal weights.
    Save to Data/agents/weights.json.
    """
    cands = _load_candidate_frames()
    for df in cands:
        try:
            X, y = _select_training_columns(df)
            if X is None or X.empty:
                continue

            # Drop non-numeric
            X = X.select_dtypes(include=["number"]).copy()
            X = X.replace([float("inf"), float("-inf")], float("nan")).dropna(axis=1, how="all")
            if X.empty:
                continue

            weights: Dict[str, float] = {}

            if y is not None:
                # Rank-based correlation (robust to outliers)
                import numpy as np
                import scipy.stats as st  # type: ignore
                try:
                    yv = pd.to_numeric(y, errors="coerce")
                    for col in X.columns:
                        xv = pd.to_numeric(X[col], errors="coerce")
                        mask = ~(xv.isna() | yv.isna())
                        if mask.sum() >= 20:
                            rho, _ = st.spearmanr(xv[mask], yv[mask])
                            weights[col] = abs(float(rho))
                except Exception:
                    pass
            else:
                # No target; use dispersion as proxy (signals with more cross-sectional spread get more weight)
                try:
                    desc = X.describe()
                    for col in X.columns:
                        std = float(desc[col]["std"]) if col in desc else 0.0
                        weights[col] = max(std, 0.0)
                except Exception:
                    for col in X.columns:
                        weights[col] = 1.0

            if not weights:
                continue

            # Normalize, map to friendly agent names when obvious
            norm = _normalize_weights(weights)

            # Persist
            meta = {"status": "ok", "note": ("corr_target" if y is not None else "dispersion"), "source": "auto_tune"}
            _save_weights_json(norm, meta)

            # Return display-friendly
            return {
                "status": "ok",
                "note": ("weights from correlation with target" if y is not None else "weights from feature dispersion"),
                "weights": [{"agent": k, "weight": v} for k, v in norm.items()],
            }
        except Exception:
            continue

    # If we got here, we could not find usable data; save equal weights
    eq = _normalize_weights({k: 1.0 for k in DEFAULT_AGENTS})
    _save_weights_json(eq, {"status": "fallback", "note": "no usable training data; equal weights"})
    return {
        "status": "fallback",
        "note": "No usable training data found; saved equal weights.",
        "weights": [{"agent": k, "weight": v} for k, v in eq.items()],
    }