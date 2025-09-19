# Program/setup_helper.py (Step 2)
from __future__ import annotations
import os, csv, json
from pathlib import Path
from typing import Dict, List, Tuple

APP_NAME = "AstroLotto"
APP_VERSION = "v11-step2"

PROG_DIR = Path(__file__).resolve().parent
ROOT = PROG_DIR.parent
DATA = Path(os.environ.get("ASTRO_DATA_DIR", ROOT / "Data"))
EXTRAS = ROOT / "Extras"

REQUIRED_DIRS = [
    DATA,
    DATA / "cache",
    DATA / "logs",
    DATA / "models",
    DATA / "quantum_hints",
    DATA / "quantum_inbox",
]

PREDICTION_CSVS = [
    "powerball_predictions.csv",
    "megamillions_predictions.csv",
    "cash5_predictions.csv",
    "pick3_predictions.csv",
    "luckyforlife_predictions.csv",
    "colorado_lottery_predictions.csv",
]

MIN_HEADERS: Dict[str, List[str]] = {
    "powerball_predictions.csv": ["draw_date","white_balls","powerball","notes"],
    "megamillions_predictions.csv": ["draw_date","white_balls","megaball","notes"],
    "cash5_predictions.csv": ["draw_date","picks","notes"],
    "pick3_predictions.csv": ["draw_date","digits","notes"],
    "luckyforlife_predictions.csv": ["draw_date","white_balls","luckyball","notes"],
    "colorado_lottery_predictions.csv": ["draw_date","picks","notes"],
}

def ensure_directories() -> List[str]:
    actions = []
    for d in REQUIRED_DIRS:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            actions.append(f"created: {d}")
    return actions

def _ensure_csv(path: Path, headers: List[str]) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(headers)
    return True

def ensure_prediction_csvs() -> List[str]:
    actions = []
    for name in PREDICTION_CSVS:
        p = DATA / name
        wrote = _ensure_csv(p, MIN_HEADERS.get(name, ["draw_date","values","notes"]))
        if wrote:
            actions.append(f"created: {p.name}")
    return actions

def ensure_requirements() -> List[str]:
    actions = []
    req = EXTRAS / "requirements.txt"
    if not req.exists():
        req.parent.mkdir(parents=True, exist_ok=True)
        req.write_text("\n".join([
            "streamlit>=1.37",
            "pandas>=2.2",
            "requests>=2.32",
            "python-dateutil>=2.9",
            "numpy>=1.26",
            "scikit-learn>=1.5",
        ]) + "\n", encoding="utf-8")
        actions.append("created: Extras/requirements.txt")
    return actions

def first_run_setup() -> Tuple[list, dict]:
    actions = []
    actions += ensure_directories()
    actions += ensure_prediction_csvs()
    actions += ensure_requirements()
    status = {"ok":"true"}
    return actions, status
