from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
import math
import json

def _data_dir_from(file_here: Path) -> Path:
    # climb to find Data folder
    for up in [file_here, *file_here.parents]:
        cand = up / "Data"
        if cand.is_dir():
            return cand
    d = file_here.parent / "Data"
    d.mkdir(parents=True, exist_ok=True)
    return d

def list_csvs(data_root: Path) -> List[Path]:
    # shallow + common subfolders
    globs = ["*.csv", "backups/*.csv", "reports/*.csv", "snapshots/*.csv"]
    out: List[Path] = []
    for pat in globs:
        out.extend(sorted(data_root.glob(pat)))
    # dedupe while preserving order
    seen = set()
    uniq = []
    for p in out:
        if p not in seen:
            seen.add(p); uniq.append(p)
    return uniq

def _safe_read_csv(path: Path, max_rows: int = 500000) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, low_memory=False)
        if len(df) > max_rows:
            df = df.tail(max_rows).copy()
        return df
    except Exception as e:
        return pd.DataFrame()

def _numeric_cols(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

def _date_cols(df: pd.DataFrame) -> List[str]:
    guess = []
    for c in df.columns:
        if "date" in c.lower() or "asof" in c.lower() or "time" in c.lower():
            guess.append(c)
    return guess

def analyze_csv(path: Path) -> Dict[str, Any]:
    df = _safe_read_csv(path)
    res: Dict[str, Any] = {"path": str(path), "exists": path.exists(), "rows": int(df.shape[0]), "cols": int(df.shape[1])}
    if df.empty:
        res.update({"note": "empty or unreadable"})
        return res

    # dtypes (simple)
    dtypes = {c: str(df[c].dtype) for c in df.columns}
    res["dtypes"] = dtypes

    # missingness
    na_counts = df.isna().sum().to_dict()
    na_pct = {k: (float(v)/len(df) if len(df) else 0.0) for k,v in na_counts.items()}
    res["missing"] = {"count": na_counts, "pct": na_pct}

    # dupes
    try:
        dup_rows = int(df.duplicated().sum())
    except Exception:
        dup_rows = 0
    res["duplicates"] = dup_rows

    # constant columns
    const_cols = []
    for c in df.columns:
        try:
            if df[c].nunique(dropna=False) <= 1:
                const_cols.append(c)
        except Exception:
            pass
    res["constant_cols"] = const_cols

    # numeric summaries + simple outliers (z>4)
    numeric = _numeric_cols(df)
    num_summary = {}
    outliers = {}
    for c in numeric:
        s = pd.to_numeric(df[c], errors="coerce")
        desc = {"min": float(np.nanmin(s)) if np.isfinite(np.nanmin(s)) else None,
                "p25": float(np.nanpercentile(s, 25)) if s.notna().any() else None,
                "median": float(np.nanmedian(s)) if s.notna().any() else None,
                "mean": float(np.nanmean(s)) if s.notna().any() else None,
                "p75": float(np.nanpercentile(s, 75)) if s.notna().any() else None,
                "max": float(np.nanmax(s)) if np.isfinite(np.nanmax(s)) else None}
        num_summary[c] = desc
        try:
            z = (s - np.nanmean(s)) / (np.nanstd(s) + 1e-9)
            outliers[c] = int(((z.abs() > 4.0) & s.notna()).sum())
        except Exception:
            outliers[c] = None
    res["numeric"] = num_summary
    res["outliers_gt4sd"] = outliers

    # date span on guessed cols
    date_info = {}
    for c in _date_cols(df):
        try:
            s = pd.to_datetime(df[c], errors="coerce", utc=True)
            date_info[c] = {"min": s.min().isoformat() if s.notna().any() else None,
                            "max": s.max().isoformat() if s.notna().any() else None}
        except Exception:
            date_info[c] = {"min": None, "max": None}
    res["dates"] = date_info

    return res

def summarize_for_humans(qa: Dict[str, Any]) -> str:
    if not qa.get("exists", False):
        return f"{qa.get('path','?')}: file not found."
    if qa.get("rows", 0) == 0:
        return f"{qa.get('path')}: file is empty or unreadable."
    rows = qa["rows"]; cols = qa["cols"]
    msg = [f"{qa.get('path')}: {rows} rows Ã {cols} columns."]
    # big missing cols
    bad = [c for c,p in (qa.get("missing",{}).get("pct",{}) or {}).items() if p >= 0.3]
    if bad:
        msg.append(f"{len(bad)} columns have â¥30% missing: {', '.join(sorted(bad)[:8])}{'...' if len(bad)>8 else ''}.")
    # duplicates
    d = qa.get("duplicates", 0)
    if d:
        msg.append(f"{d} duplicate rows detected.")
    # constants
    consts = qa.get("constant_cols", [])
    if consts:
        msg.append(f"{len(consts)} columns are constant (no variance): {', '.join(sorted(consts)[:8])}{'...' if len(consts)>8 else ''}.")
    # outliers
    outs = qa.get("outliers_gt4sd", {})
    heavy = [c for c,n in outs.items() if isinstance(n,int) and n>0]
    if heavy:
        msg.append(f"Potential outliers in: {', '.join(sorted(heavy)[:10])}{'...' if len(heavy)>10 else ''}.")
    # dates
    di = qa.get("dates", {})
    if di:
        parts = []
        for c, span in di.items():
            if span.get("min") or span.get("max"):
                parts.append(f"{c} [{span.get('min','?')} -> {span.get('max','?')}]")
        if parts:
            msg.append("Date spans: " + "; ".join(parts[:4]) + ("..." if len(parts)>4 else ""))
    return " ".join(msg)

def llm_explain(qa: Dict[str, Any]) -> str | None:
    try:
        # local only (GPT4All); fallback: None
        from .local_llm import open_model  # type: ignore
        m = open_model()
        if m is None:
            return None
        prompt = (
            "You are a data quality assistant. Given this JSON summary of a CSV, write a concise, actionable summary "
            "including 3-6 bullets (issues + suggested fixes). Avoid technical jargon; target a power user. "
            + f"JSON: {json.dumps(qa)[:4000]}"
        )
        with m.chat_session():
            out = m.generate(prompt, max_tokens=220, temp=0.2)
        return str(out).strip()
    except Exception:
        return None