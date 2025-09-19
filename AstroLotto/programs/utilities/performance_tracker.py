# utilities/performance_tracker.py
from __future__ import annotations
import json
import math
import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
except Exception:
    pd = None  # we will still work in a degraded, CSV-only mode

DATA_DIR = Path("Data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

PREDICTIONS_LOG = DATA_DIR / "predictions_log.csv"
OUTCOMES_LOG    = DATA_DIR / "outcomes_log.csv"

# -----------------------------
# Logging helpers (safe no-op if files missing)
# -----------------------------

def _ensure_csv_headers(path: Path, headers: List[str]) -> None:
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

def log_predictions(game: str, draw_date: Any, picks: List[Dict[str, Any]]) -> None:
    """
    Append a record of the predictions made for a draw.
    - game: "powerball", etc.
    - draw_date: date/datetime (string accepted)
    - picks: list like [{"white":[...], "special":X, "notes":"..."}, ...]
    """
    _ensure_csv_headers(PREDICTIONS_LOG, ["ts_utc","game","draw_date","picks_json"])
    ts = dt.datetime.utcnow().isoformat()
    row = [ts, str(game), str(draw_date), json.dumps(picks, ensure_ascii=False)]
    with PREDICTIONS_LOG.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)

def log_outcome(game: str, draw_date: Any, winning_white: List[int], winning_special: Optional[int]) -> None:
    """
    Log the official outcome for a draw (to enable basic accuracy stats).
    """
    _ensure_csv_headers(OUTCOMES_LOG, ["game","draw_date","winning_white","winning_special"])
    row = [str(game), str(draw_date), json.dumps(list(map(int, winning_white))), "" if winning_special is None else int(winning_special)]
    with OUTCOMES_LOG.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)

# -----------------------------
# Accuracy snapshot & retro memory
# -----------------------------

def _recent_hit_rate(days: int = 120) -> float:
    """
    Compute a rough hit-rate proxy in the last `days` based on intersection
    between logged predictions and outcomes. Returns 0..1.
    If we lack data, return 0.0 (neutral).
    """
    if pd is None or not PREDICTIONS_LOG.exists() or not OUTCOMES_LOG.exists():
        return 0.0

    try:
        pred = pd.read_csv(PREDICTIONS_LOG, parse_dates=["ts_utc"], keep_default_na=False)
        outc = pd.read_csv(OUTCOMES_LOG, keep_default_na=False)
        if pred.empty or outc.empty:
            return 0.0

        cutoff = dt.datetime.utcnow() - dt.timedelta(days=days)
        pred = pred[pred["ts_utc"] >= pd.Timestamp(cutoff)]
        if pred.empty:
            return 0.0

        # Parse JSON columns
        import json as _json
        outc["winning_white"] = outc["winning_white"].apply(lambda x: [] if pd.isna(x) else _json.loads(x) if isinstance(x,str) and x.strip().startswith("[") else [])
        # Keep only common draw_date rows
        merged = pred.merge(outc, how="inner", on=["game","draw_date"])
        if merged.empty:
            return 0.0

        # Score: share of picks that hit at least 1 white number (very simple proxy)
        def _score_row(r):
            try:
                picks = _json.loads(r["picks_json"])
                win = set(map(int, r["winning_white"]))
                if not picks:
                    return 0.0
                hits = 0
                for p in picks:
                    ws = set(map(int, p.get("white",[])))
                    if ws & win:
                        hits += 1
                return float(hits) / float(len(picks))
            except Exception:
                return 0.0

        hit_rates = merged.apply(_score_row, axis=1)
        if len(hit_rates) == 0:
            return 0.0
        # Average across merged rows
        return float(max(0.0, min(1.0, hit_rates.mean())))
    except Exception:
        return 0.0

def retro_memory_adjust(default_memory: float = 0.35, days: int = 120) -> float:
    """
    Return an adjusted 'memory' parameter for retrocausal weighting based on recent
    performance. If the system has been doing better than a neutral baseline, we
    increase memory a little (stabilize trends); if worse, decrease it (be more reactive).
    Always clipped to [0.15, 0.65] with small step sizes.
    """
    baseline = 0.25   # neutral "hit something in a set" proxy
    hr = _recent_hit_rate(days=days)

    # Map performance delta into a small +/- adjustment (max ~ +/- 0.10)
    delta = hr - baseline
    adj = max(-0.10, min(0.10, 0.40 * delta))  # gentle slope

    mem = float(default_memory) + adj
    mem = max(0.15, min(0.65, mem))
    return float(mem)

# -----------------------------
# Optional helpers (safe defaults if unused)
# -----------------------------

def dow_weights(white_max: int, when: Optional[dt.date] = None):
    """
    Day-of-week weights; for now neutral (uniform). Kept for backward compat.
    """
    import numpy as np
    return np.ones(int(white_max), dtype=float) / float(max(1, int(white_max)))
