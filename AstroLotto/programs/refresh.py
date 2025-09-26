from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


from pathlib import Path
import importlib

LABEL_TO_UPDATER = {
    "Mega Millions": ("programs.services.mega_updates", "update_megamillions"),
    "Powerball": ("programs.services.powerball_updates", "update_powerball"),
    "Colorado Cash 5": ("programs.services.cash5_updates", "update_cash5"),
    "Lucky for Life": ("programs.services.lucky_updates", "update_luckyforlife"),
    "Colorado Lotto+": ("programs.services.colorado_updates", "update_colorado"),
    "Pick 3": ("programs.services.pick3_updates", "update_pick3"),
}

def refresh_one(root: Path, label: str):
    mod_name, fn_name = LABEL_TO_UPDATER[label]
    mod = importlib.import_module(mod_name)
    fn = getattr(mod, fn_name)
    return fn(root)

def refresh_all(root: Path):
    res = {}
    for label in LABEL_TO_UPDATER.keys():
        try:
            res[label] = refresh_one(root, label)
        except Exception as e:
            res[label] = e
    return res
