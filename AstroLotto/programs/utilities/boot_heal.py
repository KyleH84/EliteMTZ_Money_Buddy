# Auto-heal critical CSVs on import (safe, idempotent)
from __future__ import annotations
from pathlib import Path
import pandas as pd, re, time, shutil

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Data"

def _bak(p: Path):
    if p.exists():
        shutil.copy2(p, p.with_suffix(p.suffix + f".bak-{time.strftime('%Y%m%d-%H%M%S')}"))

def _heal_pick3():
    p = DATA / "cached_pick3_data.csv"
    if not p.exists():
        return
    try:
        _bak(p)
        df = pd.read_csv(p, dtype=str).fillna("")
        cols = [c.lower().strip() for c in df.columns]
        df.columns = cols
        ncols = [c for c in cols if c in ("n1","n2","n3")]
        wcols = [c for c in cols if c in ("white1","white2","white3")]
        if not ncols and wcols:
            df = df.rename(columns={wcols[i]: f"n{i+1}" for i in range(min(3, len(wcols)))})
            ncols = [f"n{i}" for i in range(1,4)]
        if not wcols and ncols:
            for i in range(1,4):
                df[f"white{i}"] = df.get(f"n{i}", "")
        if "draw_date" not in df.columns:
            for c in df.columns:
                if "date" in c:
                    df = df.rename(columns={c:"draw_date"}); break
            if "draw_date" not in df.columns:
                df["draw_date"] = ""
        for i in range(1,4):
            col = f"n{i}"
            if col not in df.columns:
                df[col] = ""
            s = df[col].astype(str).str.extract(r"(\d+)")[0]
            s = pd.to_numeric(s, errors="coerce")
            s = s.where((s>=0)&(s<=9))
            df[col] = s.astype("Int64")
            df[f"white{i}"] = df[col]
        df = df.dropna(subset=["n1","n2","n3"])
        out_cols = [c for c in ["draw_date","n1","n2","n3","white1","white2","white3"] if c in df.columns]
        df[out_cols].to_csv(p, index=False)
    except Exception:
        pass

def _heal_colorado_predictions():
    p = DATA / "colorado_predictions.csv"
    if not p.exists():
        return
    try:
        _bak(p)
        df = pd.read_csv(p, dtype=str).fillna("")
        cols = [c.strip().lower() for c in df.columns]
        df.columns = cols
        for c in ["white_balls","draw_date","notes"]:
            if c not in df.columns:
                df[c] = ""
        if "special" not in df.columns:
            df["special"] = ""
        def norm_white(x: str) -> str:
            s = str(x) if x is not None else ""
            nums = re.findall(r"\d+", s)
            return "[]" if not nums else "[" + ",".join(str(int(n)) for n in nums) + "]"
        df["white_balls"] = df["white_balls"].apply(norm_white)
        df["notes"] = df["notes"].astype(str)
        df = df[["white_balls","special","draw_date","notes"]]
        df.to_csv(p, index=False)
    except Exception:
        pass

def run():
    _heal_pick3()
    _heal_colorado_predictions()

try:
    run()
except Exception:
    pass
