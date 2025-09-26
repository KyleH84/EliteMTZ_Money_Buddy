from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/repair.py
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

# Canonical special column names per game
SPECIAL_CANON = {
    "powerball": "powerball",
    "megamillions": "mega_ball",
    "luckyforlife": "lucky_ball",
}

# Acceptable aliases to detect existing special column
SPECIAL_ALIASES = {
    "powerball": ["powerball","power_ball","pb","pb_ball","power","red","bonus","special"],
    "megamillions": ["mega_ball","megaball","mega","mb","mega ball","bonus","special"],
    "luckyforlife": ["lucky_ball","luckyball","lucky","lb","lucky ball","bonus","special"],
}

def _find_special_col(df: pd.DataFrame, game: str) -> Optional[str]:
    aliases = SPECIAL_ALIASES.get(game, [])
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc in aliases:
            return c
    return None

def _ensure_prediction_schema(path: Path, game: str) -> Tuple[bool, str]:
    """Ensure predictions CSV has columns: draw_date, white_balls, special, notes."""
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return False, f"{path.name}: unreadable: {e}"
    changed = False
    # ensure draw_date
    if "draw_date" not in df.columns:
        if "date" in df.columns:
            df = df.rename(columns={"date":"draw_date"}); changed = True
        else:
            df.insert(0, "draw_date", "")
            changed = True
    # ensure white_balls
    if "white_balls" not in df.columns:
        # try to combine n1..n6 or white1..white5 into a string
        candidate_cols = [c for c in df.columns if str(c).lower().startswith(("n","white"))]
        if candidate_cols:
            def _fmt_row(row):
                vals = []
                for c in candidate_cols:
                    v = row.get(c, "")
                    try:
                        if pd.isna(v): continue
                    except Exception:
                        pass
                    vals.append(str(int(v)) if str(v).isdigit() else str(v))
                return " ".join([v for v in vals if v])
            df["white_balls"] = df.apply(_fmt_row, axis=1)
        else:
            df["white_balls"] = ""
        changed = True
    # ensure special
    if "special" not in df.columns:
        # look for known names
        for nm in ("powerball","mega_ball","lucky_ball","bonus"):
            if nm in df.columns:
                df = df.rename(columns={nm:"special"})
                break
        else:
            df["special"] = ""
        changed = True
    # ensure notes
    if "notes" not in df.columns:
        df["notes"] = "legacy"
        changed = True
    if changed:
        # reorder minimally
        cols = list(df.columns)
        want = ["draw_date","white_balls","special","notes"]
        ordered = [c for c in want if c in cols] + [c for c in cols if c not in want]
        df = df[ordered]
        df.to_csv(path, index=False)
        return True, f"{path.name}: migrated to standard schema"
    return True, f"{path.name}: already standard"

def _fix_cache_special(DATA: Path, game: str, filename: str) -> Tuple[bool, str]:
    path = DATA / filename
    if not path.exists():
        return False, f"{filename}: missing"
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return False, f"{filename}: unreadable: {e}"
    canon = SPECIAL_CANON.get(game)
    if not canon:
        return True, f"{filename}: no special column required"
    if canon in df.columns:
        return True, f"{filename}: special column OK ({canon})"
    # try to find alias
    alias = _find_special_col(df, game)
    if alias:
        df = df.rename(columns={alias: canon})
        df.to_csv(path, index=False)
        return True, f"{filename}: renamed special '{alias}' -> '{canon}'"
    # otherwise add empty column so diagnostics pass (backfill may fill later)
    df[canon] = pd.NA
    df.to_csv(path, index=False)
    return True, f"{filename}: added empty special column '{canon}'"

def run(DATA: Path) -> str:
    msgs = []
    # Fix caches
    msgs.append("== Cache special columns ==")
    msgs.append(_fix_cache_special(DATA, "powerball", "cached_powerball_data.csv")[1])
    msgs.append(_fix_cache_special(DATA, "luckyforlife", "cached_luckyforlife_data.csv")[1])
    # Predictions schema
    msgs.append("\n== Prediction CSV schemas ==")
    for game, fname in [
        ("powerball","powerball_predictions.csv"),
        ("megamillions","megamillions_predictions.csv"),
        ("cash5","cash5_predictions.csv"),
        ("pick3","pick3_predictions.csv"),
        ("luckyforlife","luckyforlife_predictions.csv"),
        ("colorado","colorado_lottery_predictions.csv"),
    ]:
        p = DATA/fname
        if not p.exists():
            # create an empty scaffold so app can append safely
            import csv, datetime as dt
            with p.open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["draw_date","white_balls","special","notes"])
            msgs.append(f"{fname}: created empty scaffold")
            continue
        ok, m = _ensure_prediction_schema(p, game)
        msgs.append(m)
    return "\n".join(msgs)
