from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/chaos_signals.py
from pathlib import Path
from datetime import date
import hashlib, pandas as pd, numpy as np, os

def _kp_for_date(d: date, extras_dir: Path, program_dir: Path) -> float|None:
    for base in (extras_dir / "static", program_dir / "static"):
        f = base / "kp_index.csv"
        if f.exists():
            try:
                df = pd.read_csv(f)
                df["date"]=pd.to_datetime(df["date"]).dt.date
                row = df[df["date"]==d]
                if not row.empty:
                    return float(row.iloc[0]["kp"])
                # nearest neighbor if exact missing
                idx = (df["date"] - pd.Timestamp(d)).abs().argsort().iloc[0]
                return float(df.iloc[idx]["kp"])
            except Exception:
                continue
    return None

def chaos_level_for_date(d: date) -> float:
    # Kp-driven + jitter
    extras = Path(os.environ.get("ASTRO_EXTRAS_DIR","Extras"))
    program = Path(os.environ.get("ASTRO_PROGRAM_DIR","Program"))
    kp = _kp_for_date(d, extras, program)
    base = 0.5 if kp is None else min(1.0, max(0.0, (kp/9.0)))
    h = int(hashlib.md5(str(d).encode()).hexdigest(), 16)
    jitter = ((h % 1000) / 1000.0 - 0.5) * 0.2
    level = min(1.0, max(0.0, base + jitter))
    return float(level)
