from __future__ import annotations
import os
from pathlib import Path

def resolve_data_dir(app_root: Path, env_var_name: str = "APP_DATA_DIR", default_subdir: str = "Data") -> Path:
    """Return a writable data directory, preferring env var; else app_root/default_subdir; else /tmp fallback.
    Creates the directory if it doesn't exist.
    """
    # 1) Environment override
    env = os.getenv(env_var_name, "").strip()
    candidates = []
    if env:
        candidates.append(Path(env).expanduser())

    # 2) Repo-local Data/
    candidates.append((app_root / default_subdir))

    # 3) /tmp fallback (works on Streamlit Cloud)
    safe_name = app_root.name or "app"
    candidates.append(Path("/tmp") / safe_name / default_subdir)

    for c in candidates:
        try:
            c = c.expanduser().resolve()
        except Exception:
            # if resolve fails, use as-is
            pass
        try:
            c.mkdir(parents=True, exist_ok=True)
            # Try to touch a small file to verify writability
            testf = c / ".write_test.tmp"
            with open(testf, "w", encoding="utf-8") as f:
                f.write("ok")
            testf.unlink(missing_ok=True)
            return c
        except Exception:
            continue
    # As a last resort, return app_root
    return app_root
