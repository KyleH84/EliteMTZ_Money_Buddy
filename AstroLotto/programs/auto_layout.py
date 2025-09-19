from pathlib import Path
import json

def ensure_layout(root: str | None = None) -> None:
    base = Path(root or ".").resolve()
    data = base / "Data"
    extras = base / "Extras"
    for p in (data/"cache", data/"logs", data/"backups", extras/"models"):
        p.mkdir(parents=True, exist_ok=True)
    prefs = extras / "user_prefs.json"
    if not prefs.exists():
        prefs.write_text(json.dumps({"zip_layout_version": "11.0.bootstrap"}, indent=2), encoding="utf-8")
