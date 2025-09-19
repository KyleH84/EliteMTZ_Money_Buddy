
from __future__ import annotations
from pathlib import Path
from typing import List

# Pages listed here will be retained in the ``programs/pages`` directory when
# ``consolidate_pages`` is invoked.  Names are compared case‑insensitively
# against the stem of each ``.py`` file, without numeric prefixes or
# file extensions.  The default set keeps the main application page, the
# about page and the admin page.  We include both numeric and non‑numeric
# variants to allow either ``about.py`` or ``00_About.py`` to be retained.
WHITELIST = {
    "app main",  # historical name for the root app page (app_main.py)
    "app_main",  # explicit stem for app_main.py
    "app",       # alternative generic name for the app page
    "about",     # about page, regardless of numeric prefix
    "00_about",  # numeric prefix variant used in earlier versions
    "admin",     # admin page
}

def consolidate_pages(project_root: Path) -> dict:
    pages_dir = project_root / "programs" / "pages"
    archive_dir = pages_dir / "_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    moved, kept = [], []
    for p in sorted(pages_dir.glob("*.py")):
        name = p.stem.lower().strip()
        if name in WHITELIST:
            kept.append(p.name)
            continue
        # Never move our own _archive or __init__
        if name.startswith("_") or name == "__init__":
            kept.append(p.name)
            continue
        # Move to archive (overwrites if already there)
        target = archive_dir / p.name
        try:
            if target.exists():
                target.unlink()
            p.replace(target)
            moved.append(p.name)
        except Exception:
            # If move fails, leave it in place
            kept.append(p.name)
    return {"moved": moved, "kept": kept, "archive": str(archive_dir)}
