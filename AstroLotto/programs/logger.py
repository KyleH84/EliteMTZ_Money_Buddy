# utilities/logger.py
from __future__ import annotations
import csv, os
from pathlib import Path
from typing import Dict, List

def ensure_csv(path: str | Path, headers: List[str]) -> None:
    p = Path(path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)

def append_row(path: str | Path, row: Dict[str, str | int | float]) -> None:
    p = Path(path)
    # ensure header order matches row keys if file doesn't exist
    if not p.exists():
        ensure_csv(p, list(row.keys()))
    # if exists but empty, write headers
    if p.stat().st_size == 0:
        ensure_csv(p, list(row.keys()))
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        w.writerow(row)
