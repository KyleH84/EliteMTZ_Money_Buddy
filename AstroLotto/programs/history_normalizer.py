# Program/history_normalizer.py
from __future__ import annotations
import shutil, time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
BACKUP = DATA / "backup"
BACKUP.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "powerball": DATA / "cached_powerball_data.csv",
    "megamillions": DATA / "cached_megamillions_data.csv",
    "cash5": DATA / "cached_cash5_data.csv",
    "pick3": DATA / "cached_pick3_data.csv",
    "luckyforlife": DATA / "cached_luckyforlife_data.csv",
    "colorado": DATA / "cached_colorado_lottery_data.csv",
}

PREDICTIONS = {
    "powerball": DATA / "powerball_predictions.csv",
    "megamillions": DATA / "megamillions_predictions.csv",
    "cash5": DATA / "cash5_predictions.csv",
    "pick3": DATA / "pick3_predictions.csv",
    "luckyforlife": DATA / "luckyforlife_predictions.csv",
    "colorado": DATA / "colorado_lottery_predictions.csv",
}

def _timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")

def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def _save_backup(path: Path) -> Optional[Path]:
    if not path.exists(): return None
    b = BACKUP / f"{path.name}.bak.{_timestamp()}.csv"
    try:
        shutil.copy2(path, b)
        return b
    except Exception:
        return None

def _detect_history_schema(df: pd.DataFrame) -> Dict[str, object]:
    if df is None or df.empty:
        return {"is_history": False, "reason": "empty"}
    cols = [c.lower().strip() for c in df.columns]
    cset = set(cols)
    if "white_balls" in cset or "digits" in cset:
        return {"is_history": False, "reason": "predictions-like schema"}
    has_white = any(c.startswith("white") for c in cols)
    has_n = any(c.startswith("n") and c[1:].isdigit() for c in cols)
    has_special = ("s1" in cset) or ("special" in cset)
    looks_like_date = any("draw" in c and "date" in c for c in cols) or ("draw_date" in cset)
    long_enough = len(df) >= 200
    if looks_like_date and long_enough and (has_white or has_n):
        white_cols = [c for c in df.columns if c.lower().startswith("white")]
        if not white_cols:
            white_cols = [c for c in df.columns if c.lower().startswith("n") and c[1:].isdigit()]
            white_cols = sorted(white_cols, key=lambda x: int(x[1:]))
        special = None
        for sc in ("s1","special"):
            if sc in cset:
                for oc in df.columns:
                    if oc.lower() == sc:
                        special = oc
                        break
        date_col = None
        for oc in df.columns:
            lc = oc.lower()
            if lc == "draw_date" or ("draw" in lc and "date" in lc):
                date_col = oc
                break
        return {"is_history": True, "white_cols": white_cols, "special": special, "date_col": date_col}
    return {"is_history": False, "reason": "schema mismatch"}

def _standardize_dates(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    out = df.copy()
    try:
        out["draw_date"] = pd.to_datetime(out[date_col], errors="coerce").dt.date.astype(str)
    except Exception:
        out["draw_date"] = out[date_col].astype(str)
    return out

def _normalize_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64")
    return out

def _harmonize_to_cached_schema(df: pd.DataFrame, target: Path) -> pd.DataFrame:
    name = target.name
    if "powerball" in name or "megamillions" in name or "luckyforlife" in name:
        need = ["draw_date","white1","white2","white3","white4","white5","special"]
    elif "colorado" in name:
        need = ["draw_date","n1","n2","n3","n4","n5","n6"]
    elif "cash5" in name:
        need = ["draw_date","n1","n2","n3","n4","n5"]
    elif "pick3" in name:
        need = ["draw_date","n1","n2","n3"]
    else:
        need = ["draw_date"]
    out = pd.DataFrame(columns=need)

    # Set dates
    out["draw_date"] = df.get("draw_date", df.get("Draw Date", "")).astype(str)

    # Candidate numeric columns from source
    candidates = [c for c in df.columns if c.lower().startswith("white") or (c.lower().startswith("n") and c[1:].isdigit())]

    # Map by numeric order where possible
    def _col_index(c: str) -> int:
        num = "".join(ch for ch in c if ch.isdigit())
        return int(num) if num else 999

    numbers = sorted(candidates, key=lambda c: (_col_index(c), c))

    # Fill white/n columns
    fill_cols = [c for c in need if c not in ("draw_date","special")]
    for i, tgt in enumerate(fill_cols):
        if i < len(numbers):
            out[tgt] = pd.to_numeric(df[numbers[i]], errors="coerce").astype("Int64")

    # Special
    if "special" in need:
        if "special" in df.columns:
            out["special"] = pd.to_numeric(df["special"], errors="coerce").astype("Int64")
        elif len(numbers) >= len(fill_cols) + 1:
            out["special"] = pd.to_numeric(df[numbers[len(fill_cols)]], errors="coerce").astype("Int64")

    return out

def _merge_dedupe(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    if existing is None or existing.empty:
        out = new.copy()
    else:
        out = pd.concat([existing, new], ignore_index=True)
        out = out.drop_duplicates(subset=["draw_date"], keep="last")
    if not out.empty:
        out = out.sort_values(by=["draw_date"]).reset_index(drop=True)
    return out

def normalize_all(dry_run: bool = False) -> List[str]:
    logs: List[str] = []
    for game, pred_path in PREDICTIONS.items():
        if not pred_path.exists():
            continue
        df = _read_csv(pred_path)
        desc = _detect_history_schema(df)
        if not desc.get("is_history"):
            logs.append(f"{pred_path.name}: skipped ({desc.get('reason','not history')})")
            continue

        target = TARGETS.get(game)
        if not target:
            logs.append(f"{pred_path.name}: detected history but couldn't determine target cache; skipped")
            continue

        # Normalize and merge
        date_col = desc.get("date_col") or df.columns[0]
        norm = _standardize_dates(df, date_col)
        norm = _harmonize_to_cached_schema(norm, target)
        existing = _read_csv(target)
        merged = _merge_dedupe(existing, norm)

        if dry_run:
            logs.append(f"{pred_path.name}: would migrate {len(norm)} rows -> {target.name} (after merge {len(merged)} rows)")
            continue

        # backups
        b1 = _save_backup(pred_path)
        b2 = _save_backup(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(target, index=False)
        migrated = pred_path.with_name(f"{pred_path.stem}.migrated.{_timestamp()}.csv")
        try:
            pred_path.rename(migrated)
            logs.append(f"{pred_path.name}: migrated -> {target.name}; backups saved; original renamed to {migrated.name}")
        except Exception:
            logs.append(f"{pred_path.name}: migrated -> {target.name}; backups saved; could not rename original")
    return logs
