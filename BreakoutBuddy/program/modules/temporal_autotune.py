from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from pathlib import Path

# ---------- Strict per-app Data/Extras resolver (BreakoutBuddy) ----------
from pathlib import Path
import os, sys
BB_HERE     = Path(__file__).resolve()
BB_APP_ROOT = BB_HERE.parents[1]   # .../BreakoutBuddy

def _bb_cloud_roots():
    h = Path.home()
    return [
        h / "OneDrive",
        h / "OneDrive - Personal",
        h / "OneDrive - Wagstaff Law Firm",
        h / "Dropbox",
        h / "Google Drive",
        h / "Library" / "CloudStorage" / "OneDrive",
        h / "Library" / "CloudStorage" / "Dropbox",
        h / "Library" / "CloudStorage" / "GoogleDrive",
    ]

def _bb_first_existing(paths):
    for p in paths:
        try:
            p2 = Path(p).expanduser().resolve()
            if p2.exists():
                return p2
        except Exception:
            pass
    return None

def bb_resolve_dir(preferred_env_var: str, fallback_name: str):
    """
    Strict per-app order (NO repo-level fallback):
      1) Env var (abs or relative)
      2) BB_APP_ROOT/<name>
      3) CWD/<name>
      4) Cloud roots: <BreakoutBuddy>/<name>
      5) Create BB_APP_ROOT/<name>
    """
    envv = os.environ.get(preferred_env_var, "").strip()
    if envv:
        cand = (Path(envv) if os.path.isabs(envv) else (Path.cwd() / envv))
        if cand.exists():
            return cand.resolve()

    hit = _bb_first_existing([BB_APP_ROOT / fallback_name, Path.cwd() / fallback_name])
    if hit:
        return hit

    cands = []
    for root in _bb_cloud_roots():
        cands += [
            root / BB_APP_ROOT.name / fallback_name,
            root / "Projects" / BB_APP_ROOT.name / fallback_name,
        ]
    hit = _bb_first_existing(cands)
    if hit:
        return hit

    target = (BB_APP_ROOT / fallback_name).resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target

BB_DATA   = bb_resolve_dir("BREAKOUTBUDDY_DATA",   "Data")
BB_EXTRAS = bb_resolve_dir("BREAKOUTBUDDY_EXTRAS", "extras")

bb_extras_src = (BB_EXTRAS / "src")
if bb_extras_src.exists() and str(bb_extras_src) not in sys.path:
    sys.path.insert(0, str(bb_extras_src))
# ---------- end resolver ----------

# temporal_autotune.py
# Autotunes the Kozyrev coupling kappa using your CSV logs.
# Works for:
#   - BreakoutBuddy: uses bb_temporal_logs.csv + outcomes with realized labels
#   - AstroLotto:    uses temporal_logs.csv + draw results to score distributions
#
# No external deps beyond numpy/pandas.
# Author: Chad (for Kyle)
# License: MIT

import json
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import numpy as np
import pandas as pd

# ---------------------------
# Utility
# ---------------------------
def _safe_json(x):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    try:
        return json.loads(x) if isinstance(x, str) else x
    except Exception:
        return None

def _normalize(vec: np.ndarray) -> np.ndarray:
    s = np.sum(vec)
    return vec / s if s > 0 else vec

# ---------------------------
# BreakoutBuddy autotune
# ---------------------------
@dataclass
class BBOutcome:  # minimal schema if you roll your own outcomes CSV
    # One row per (run_ts, ticker) with realized label
    run_ts: int
    ticker: str
    label: float  # 0/1 or regression target

def tune_kappa_breakoutbuddy(
    logs_csv: str = str(BB_DATA / 'bb_temporal_logs.csv'),
    outcomes_csv: Optional[str] = None,
    label_col: str = "label",
    kappa_min: float = -5e16,
    kappa_max: float =  5e16,
    kappa_steps: int = 41,
    metric: str = "logloss"  # "logloss", "auc", "mse"
) -> Dict[str, float]:
    """
    Fit a single global kappa by scanning a grid and picking the best metric.
    Requires outcomes CSV to score; expected columns: run_ts, ticker, label (0/1 works best).
    If outcomes_csv is None, we fall back to comparing base vs final distribution of scores,
    which cannot identify the *best* kappa — only reports summary stats.
    """
    df = pd.read_csv(logs_csv)
    if outcomes_csv is None:
        # Fallback summary
        return {
            "warning": "No outcomes CSV provided; cannot tune kappa.",
            "mean_base": float(np.nanmean(df.get("score_base", np.nan))),
            "mean_final": float(np.nanmean(df.get("score_final", np.nan))),
            "rows": int(len(df))
        }

    out = pd.read_csv(outcomes_csv)
    # Join on (run_ts, ticker)
    keycols = ["run_ts","ticker"]
    if not set(keycols).issubset(df.columns) or not set(keycols+[label_col]).issubset(out.columns):
        raise ValueError(f"Expected columns in logs: {keycols}; in outcomes: {keycols + [label_col]}")
    d = df.merge(out[keycols + [label_col]], on=keycols, how="inner").copy()
    if d.empty:
        raise ValueError("No overlapping rows between logs and outcomes.")

    # We recorded 'delta_K' which is (∂y/∂t)*Δt_K_used; score_final = base + delta_K_used
    # For a new kappa', delta scales linearly: delta_K' = delta_K_used * (kappa'/kappa_used)
    # Where kappa_used is 'kappa' in the row (can be 0; skip those rows).
    d = d[(~d["kappa"].isna()) & (d["kappa"] != 0.0) & (~d["delta_K"].isna())].copy()
    if d.empty:
        raise ValueError("No rows with nonzero kappa and valid delta_K in logs; run with multiple kappas first.")

    kappas = np.linspace(kappa_min, kappa_max, kappa_steps)
    best = {"kappa": 0.0, "metric": float("inf") if metric=="logloss" else -float("inf")}

    # Prepare arrays
    base = d["score_base"].astype(float).to_numpy()
    used = d["kappa"].astype(float).to_numpy()
    delta_used = d["delta_K"].astype(float).to_numpy()
    y = d[label_col].astype(float).to_numpy()

    # clip base into [1e-6, 1-1e-6]
    eps = 1e-6
    base = np.clip(base, eps, 1-eps)

    for k in kappas:
        # avoid division by zero
        scale = k / used
        delta_new = delta_used * scale
        pred = np.clip(base + delta_new, eps, 1-eps)

        if metric == "logloss":
            loss = -np.mean(y * np.log(pred) + (1-y)*np.log(1-pred))
            score = -loss  # lower is better
            choose = (loss < ( -best["metric"] ))
            val = -loss
        elif metric == "mse":
            mse = np.mean((pred - y)**2)
            score = -mse
            choose = (mse < ( -best["metric"] ))
            val = -mse
        elif metric == "auc":
            # simple pairwise approximation (no sklearn)
            order = np.argsort(pred)
            y_sorted = y[order]
            # AUC via rank method
            pos = np.where(y_sorted==1)[0]
            neg = np.where(y_sorted==0)[0]
            if len(pos)==0 or len(neg)==0:
                continue
            rank_sum = np.sum(np.searchsorted(order, pos))
            # fallback quick approx: use Mann–Whitney U with ranks of predictions
            # Easier alternative: compute via brute force
            auc_cnt = 0; total = 0
            pred_all = pred
            for i in range(len(pred_all)):
                for j in range(i+1, len(pred_all)):
                    if y[i]!=y[j]:
                        total += 1
                        if (pred_all[i] > pred_all[j] and y[i]>y[j]) or (pred_all[j] > pred_all[i] and y[j]>y[i]):
                            auc_cnt += 1
                        elif pred_all[i]==pred_all[j]:
                            auc_cnt += 0.5
            auc = auc_cnt/total if total>0 else 0.5
            score = auc
            choose = (auc > best["metric"])
            val = auc
        else:
            raise ValueError("Unknown metric.")

        if choose:
            best = {"kappa": float(k), "metric": float(val)}

    return best

# ---------------------------
# AstroLotto autotune
# ---------------------------
@dataclass
class DrawResult:
    # minimal schema
    run_ts: int
    game: str
    white_winning: List[int]
    special_winning: Optional[int]

def _winner_mass_white(W: np.ndarray, winners: List[int], indexing: str = "1-based") -> float:
    # Sum the probability mass on winning numbers (white balls)
    # indexing: "1-based" for balls numbered 1..N
    mass = 0.0
    for n in winners:
        idx = n-1 if indexing=="1-based" else n
        if 0 <= idx < len(W):
            mass += float(W[idx])
    return mass

def tune_kappa_astrolotto(
    logs_csv: str = str(BB_DATA / 'temporal_logs.csv'),
    results_csv: Optional[str] = None,
    white_col: str = "white_winning",
    special_col: str = "special_winning",
    kappa_min: float = -5e16,
    kappa_max: float =  5e16,
    kappa_steps: int = 41,
    objective: str = "mass_on_winners"  # "mass_on_winners" or "top_pick_hitrate"
) -> Dict[str, float]:
    """
    Uses linearity of the logged delta vectors to scan kappa and pick the one
    that maximizes the chosen objective.

    Requires a results CSV with columns:
      - run_ts (matching the log row's run_ts)
      - white_winning (JSON list of winning white numbers, 1-based)
      - special_winning (int or null)
    """
    d = pd.read_csv(logs_csv)
    if results_csv is None:
        return {"warning": "No results CSV provided; cannot tune kappa."}
    r = pd.read_csv(results_csv)
    key = ["run_ts","game"]
    if not set(key).issubset(d.columns) or "run_ts" not in r.columns:
        raise ValueError("Expected run_ts & game in logs; run_ts in results.")
    # Parse JSON vectors
    for col in ["W_base","W_final","Sp_base","Sp_final"]:
        if col in d.columns:
            d[col] = d[col].apply(_safe_json)
    # Merge results
    m = d.merge(r[["run_ts", white_col, special_col]], on="run_ts", how="inner").copy()
    if m.empty:
        raise ValueError("No overlapping rows between logs and results.")
    # We also need the delta vectors and the kappa used.
    # If not present, cannot reconstruct.
    # Diagnostics keys live inside 'diagnostics' dumps? In our logging, we stored Et,Et0,dtK and delta vectors.
    # Extract diagnostics from dict-like columns if available.
    # For safety, try columns and fallback to empty.
    # (In our earlier logger we put delta_W in diagnostics, not as a separate column; if absent we can't rescale.)
    if "diagnostics" in m.columns:
        # not used in our current schema; keep placeholder
        pass
    # Pull delta vectors if we stored them (optional)
    has_dw = "delta_W" in m.columns
    has_dsp = "delta_Sp" in m.columns or "delta_V" in m.columns  # name may vary
    if not has_dw and "delta_W" not in m.columns:
        # Try to reconstruct deltas from base/final and kappa used:
        # delta_used_vec = W_final - W_base (before renorm) — but we only stored renormalized
        # So we cannot recover exact direction; we must skip vector rescale without logged deltas.
        pass

    kappas = np.linspace(kappa_min, kappa_max, kappa_steps)
    best = {"kappa": 0.0, "objective": -float("inf")}

    def _to_vec(x):
        arr = np.asarray(x, dtype=float)
        s = arr.sum()
        return arr/s if s>0 else arr

    for k in kappas:
        scores = []
        for _, row in m.iterrows():
            Wb = _to_vec(row["W_base"]) if isinstance(row.get("W_base"), (list, tuple)) or isinstance(row.get("W_base"), np.ndarray) else _safe_json(row.get("W_base"))
            Wf = _to_vec(row["W_final"]) if isinstance(row.get("W_final"), (list, tuple)) or isinstance(row.get("W_final"), np.ndarray) else _safe_json(row.get("W_final"))
            if Wb is None:
                continue
            Wb = np.asarray(Wb, dtype=float)
            # We need a delta direction. If we logged delta_W, use it; else approximate by (Wf - Wb).
            if "delta_W" in row and isinstance(row["delta_W"], (list, tuple)):
                dW_used = np.asarray(row["delta_W"], dtype=float)
            else:
                if isinstance(Wf, (list, tuple, np.ndarray)):
                    dW_used = np.asarray(Wf, dtype=float) - Wb
                else:
                    # cannot proceed without a delta direction
                    continue
            # scale delta to new kappa (needs kappa_used)
            k_used = float(row.get("kappa", 0.0)) if "kappa" in row else 0.0
            if k_used == 0.0:
                # skip rows where no Kozyrev was applied — they carry no directional info
                continue
            scale = k / k_used
            Wk = _normalize(Wb + dW_used * scale)
            # score objective
            winners = _safe_json(row.get(white_col))
            if winners is None:
                continue
            score = _winner_mass_white(Wk, winners)
            scores.append(score)
        if len(scores)==0:
            continue
        avg = float(np.mean(scores))
        if avg > best["objective"]:
            best = {"kappa": float(k), "objective": avg}

    return best

if __name__ == "__main__":
    # Minimal smoke test (no files present in this environment)
    print("temporal_autotune module ready. See functions: tune_kappa_breakoutbuddy, tune_kappa_astrolotto")
