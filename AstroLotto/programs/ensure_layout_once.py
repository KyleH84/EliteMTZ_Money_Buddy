"""
ensure_layout_once.py
Run this once (or leave it in place; it's safe) to enforce the directory layout:
- Program/             (code lives here; we don't touch your other files)
- Data/                (CSV caches, logs, backups only)
    cache/
    logs/
    backups/
- Extras/              (add‑ons live here)
    models/
    .venv311/          (Python venv; created by RUN_AstroLotto.bat)
    requirements.txt
    user_prefs.json

If folders are missing, they're created. If "models" exists under Data, it's moved to Extras/models.
No deletes; only creates or moves to the correct spot.
"""
from __future__ import annotations
import os, shutil, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # Program/../
DATA = ROOT / "Data"
EXTRAS = ROOT / "Extras"
MODELS_DST = EXTRAS / "models"
CACHE = DATA / "cache"
LOGS = DATA / "logs"
BACKUPS = DATA / "backups"

def _mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def ensure_layout(verbose: bool = True):
    _mkdir(DATA); _mkdir(EXTRAS)
    for p in (CACHE, LOGS, BACKUPS, MODELS_DST):
        _mkdir(p)

    # If someone accidentally put models under Data/, move them.
    bad_models = DATA / "models"
    if bad_models.exists() and bad_models.is_dir():
        # move contents without deleting source
        for child in bad_models.iterdir():
            dst = MODELS_DST / child.name
            try:
                if child.is_dir():
                    shutil.copytree(child, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(child, dst)
            except Exception as e:
                if verbose: print("[WARN] Could not move", child, "->", dst, e)

    # Ensure prefs + requirements placeholders if missing
    req = EXTRAS / "requirements.txt"
    if not req.exists():
        req.write_text("streamlit\npandas\nnumpy\n", encoding="utf-8")
    prefs = EXTRAS / "user_prefs.json"
    if not prefs.exists():
        prefs.write_text(json.dumps({"zip_layout_version": "10.9.fix2"}, indent=2), encoding="utf-8")

    if verbose:
        print("[OK] Layout ensured at", ROOT)

if __name__ == "__main__":
    ensure_layout()
