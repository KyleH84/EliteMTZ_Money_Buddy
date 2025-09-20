from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/utilities/config.py
"""
Config module used by ensemble/future_feed, app_main, etc.
Restored & extended for v11 Rebuild (compatible with v10.9 callers).

Exports:
- data_dir: Path to Data/
- extras_dir: Path to Extras/
- load_user_config() -> dict
- save_user_config(cfg: dict) -> None
"""

from pathlib import Path
import os, json, tempfile, shutil

# Project root = Program/.. (two levels up from this file)
ROOT = Path(__file__).resolve().parents[2]

# Allow overrides via environment variables, otherwise default to project dirs
DATA_DIR = Path(os.environ.get("ASTRO_DATA_DIR", ROOT / "Data")).resolve()
EXTRAS_DIR = Path(os.environ.get("ASTRO_EXTRAS_DIR", ROOT / "Extras")).resolve()

# Backwards-compat aliases (v10.9 code expects these names)
data_dir = DATA_DIR
extras_dir = EXTRAS_DIR

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXTRAS_DIR.mkdir(parents=True, exist_ok=True)

# User-config path (JSON). Keep it simple and robust.
CONFIG_PATH = EXTRAS_DIR / "config.json"

def load_user_config() -> dict:
    """
    Load user config from Extras/config.json.
    If the file is missing or invalid, return an empty dict.
    Never raises for common read/parse issues.
    """
    try:
        if CONFIG_PATH.exists():
            text = CONFIG_PATH.read_text(encoding="utf-8", errors="ignore")
            if text.strip():
                return json.loads(text)
    except Exception:
        pass
    return {}

def save_user_config(cfg: dict) -> None:
    """
    Save user config atomically to Extras/config.json.
    Creates Extras/ if needed.
    """
    EXTRAS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        # atomic-ish replace
        if CONFIG_PATH.exists():
            CONFIG_PATH.unlink()
        tmp.rename(CONFIG_PATH)
    except Exception:
        # best-effort fallback
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2, ensure_ascii=False)
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
