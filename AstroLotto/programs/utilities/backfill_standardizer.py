from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd

# Standard filenames we expect in the project root
STANDARD_FILENAMES: Dict[str, str] = {
    "powerball": "powerball.csv",
    "mega_millions": "mega_millions.csv",
    "lucky_for_life": "lucky_for_life.csv",
    "colorado_lottery": "colorado_lottery.csv",
    "cash5": "cash5.csv",
    "pick3": "pick3.csv",
}

# Possible column name aliases for the draw date
DATE_ALIASES = ["draw_date", "date", "drawDate", "DrawDate", "DRAW_DATE", "Draw_Date"]

def _find_date_col(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        if c in DATE_ALIASES:
            return c
    # fuzzy
    for c in df.columns:
        lc = c.lower().replace(" ", "").replace("_", "")
        if "draw" in lc and "date" in lc:
            return c
    if "date" in [c.lower() for c in df.columns]:
        return [c for c in df.columns if c.lower()=="date"][0]
    return None

def _normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    col = _find_date_col(df)
    if not col:
        return df  # nothing to do
    df = df.copy()
    df.rename(columns={col: "draw_date"}, inplace=True)
    df["draw_date"] = pd.to_datetime(df["draw_date"], errors="coerce").dt.date
    return df

def audit_all(workdir: Path) -> pd.DataFrame:
    rows = []
    for game, fname in STANDARD_FILENAMES.items():
        p = workdir / fname
        status = "missing"
        n_rows = 0
        min_d = max_d = None
        dupes = 0
        if p.exists():
            try:
                df = pd.read_csv(p)
                df = _normalize_dates(df)
                n_rows = len(df)
                if "draw_date" in df.columns:
                    min_d = str(df["draw_date"].min())
                    max_d = str(df["draw_date"].max())
                    dupes = int(df.duplicated(subset=["draw_date"]).sum())
                status = "ok"
            except Exception as e:
                status = f"error: {e}"
        rows.append({
            "game": game, "file": fname, "status": status, "rows": n_rows,
            "min_draw_date": min_d, "max_draw_date": max_d, "duplicate_dates": dupes
        })
    import pandas as pd
    return pd.DataFrame(rows)

def _backup(p: Path):
    bak = p.with_suffix(p.suffix + ".bak")
    try:
        if p.exists():
            p.replace(bak)
            bak.replace(p)  # restore to keep original path, but ensure backup exists via copy trick
            # If replace roundtrip failed to create a real backup, fall back to write_bytes
    except Exception:
        data = p.read_bytes()
        (p.parent / (p.name + ".bak")).write_bytes(data)

def standardize_all(workdir: Path) -> pd.DataFrame:
    results: List[Dict[str, str]] = []
    for game, fname in STANDARD_FILENAMES.items():
        p = workdir / fname
        if not p.exists():
            results.append({"game": game, "file": fname, "result": "missing"})
            continue
        try:
            df = pd.read_csv(p)
            df = _normalize_dates(df)
            if "draw_date" in df.columns:
                before = len(df)
                df = df.drop_duplicates(subset=["draw_date"]).sort_values("draw_date")
                after = len(df)
                # backup original safely
                content = p.read_bytes()
                (p.parent / (p.name + ".bak")).write_bytes(content)
                df.to_csv(p, index=False)
                results.append({"game": game, "file": fname, "result": f"ok (dedup {before-after})"})
            else:
                results.append({"game": game, "file": fname, "result": "no date column"})
        except Exception as e:
            results.append({"game": game, "file": fname, "result": f"error: {e}"})
    import pandas as pd
    return pd.DataFrame(results)
