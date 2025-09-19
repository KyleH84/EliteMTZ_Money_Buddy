
"""
backfill_sanity_check.py
------------------------
Run with the same virtualenv as the app:
    .venv311\Scripts\python.exe backfill_sanity_check.py

What it does:
- Locates draw-history CSVs for each game in the current folder
- Reads the data and prints:
    * file used
    * row count
    * detected date column
    * min/max draw dates
- Warns if the latest date is already recent (so backfill would add +0)
- Warns if the file/headers look off
"""

from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import datetime as dt

CANDIDATE_FILENAMES = {
    "powerball": [
        "powerball_draws.csv", "powerball_history.csv", "powerball.csv",
        "Powerball_draws.csv", "PowerBall.csv"
    ],
    "mega_millions": [
        "megamillions_draws.csv", "mega_millions_draws.csv", "megamillions_history.csv",
        "mega_millions.csv", "MegaMillions.csv"
    ],
    "lucky_for_life": [
        "luckyforlife_draws.csv", "lucky_for_life_draws.csv", "luckyforlife_history.csv",
        "lucky_for_life.csv"
    ],
    "colorado_lottery": [
        "coloradolotto_draws.csv", "colorado_lottery_draws.csv", "coloradolottery_history.csv",
        "colorado_lottery.csv"
    ],
    "cash5": [
        "cash5_draws.csv", "cash_5_draws.csv", "cash5_history.csv", "cash5.csv"
    ],
    "pick3": [
        "pick3_draws.csv", "pick_3_draws.csv", "pick3_history.csv", "pick3.csv"
    ],
}

DATE_HEADER_CANDIDATES = ["draw_date", "Draw Date", "date", "Date", "DRAW_DATE", "drawDate"]

def find_file(name_list):
    here = Path(".")
    for nm in name_list:
        p = here / nm
        if p.exists():
            return p
    return None

def find_date_column(df: pd.DataFrame):
    for c in DATE_HEADER_CANDIDATES:
        if c in df.columns:
            return c
    # try a fuzzy guess
    for c in df.columns:
        if "date" in c.lower():
            return c
    return None

def coerce_date(series: pd.Series):
    # Common formats
    for fmt in [None, "%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"]:
        try:
            return pd.to_datetime(series, format=fmt, errors="raise")
        except Exception:
            pass
    # Fallback: best-effort
    return pd.to_datetime(series, errors="coerce")

def audit_game(game_key: str):
    f = find_file(CANDIDATE_FILENAMES[game_key])
    print(f"\n=== {game_key} ===")
    if not f:
        print("  [WARN] No CSV found (checked:", ", ".join(CANDIDATE_FILENAMES[game_key]), ")")
        return
    try:
        df = pd.read_csv(f)
    except Exception as e:
        print(f"  [ERROR] Failed to read {f.name}: {e}")
        return
    print(f"  file: {f.name}   rows: {len(df)}")
    if len(df)==0:
        print("  [WARN] CSV is empty.")
        return
    date_col = find_date_column(df)
    if not date_col:
        print("  [ERROR] Could not detect a date column. Columns:", list(df.columns))
        return
    dt_series = coerce_date(df[date_col])
    if dt_series.isna().all():
        print(f"  [ERROR] Date parsing failed for column '{date_col}'. First values:", df[date_col].head(5).tolist())
        return
    min_d = dt_series.min()
    max_d = dt_series.max()
    print(f"  date column: '{date_col}'   range: {min_d.date()} .. {max_d.date()}")
    days_old = (dt.date.today() - max_d.date()).days
    if days_old <= 2:
        print(f"  [OK] Latest draw is {days_old} day(s) old. Backfill may correctly add +0.")
    elif days_old <= 14:
        print(f"  [INFO] Latest draw is {days_old} day(s) old. If +0, source parser may be lagging or silent-failing.")
    else:
        print(f"  [WARN] Latest draw is {days_old} day(s) old. Expect backfill to add many rows unless the fetcher skipped.")

def main():
    for k in ["powerball", "mega_millions", "lucky_for_life", "colorado_lottery", "cash5", "pick3"]:
        audit_game(k)

if __name__ == "__main__":
    main()
