from __future__ import annotations


# cloud_csv_shim.py
# -------------------------------------------------------------
# Import this ONCE near the top of streamlit_app.py to route ALL
# pandas CSV reads/writes to Supabase Storage ("tables" bucket).
#
#   try:
#       import cloud_csv_shim  # patches pandas
#   except Exception as e:
#       print("CSV shim disabled:", e)
#
# Requirements:
#   - env vars (or Streamlit secrets → env) set:
#       SUPABASE_URL, SUPABASE_KEY
#   - requirements.txt includes: supabase, pandas, pyarrow
#   - Supabase bucket 'tables' exists (private is fine)
# -------------------------------------------------------------

import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

# --------- minimal Supabase helpers (no relative imports) ---------
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_TABLES = os.getenv("SUPABASE_BUCKET_TABLES", "tables")

def _sb():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY not configured")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def _sb_download_bytes(path: str) -> bytes | None:
    try:
        return _sb().storage.from_(BUCKET_TABLES).download(path)
    except Exception:
        return None

def _sb_upload_bytes(path: str, b: bytes) -> None:
    _sb().storage.from_(BUCKET_TABLES).upload(
        path, b, file_options={"cache-control": "no-cache", "upsert": "true"}
    )

# --------- name mapping from path → {app}/{table}.parquet ---------
_VALID = re.compile(r"[^a-zA-Z0-9_]+")

def _guess_app(p: Path) -> str:
    s = str(p).lower().replace("\\", "/")
    if "/astrolotto/" in s or "/astro_lotto/" in s or "/astro/" in s:
        return "AL"
    if "/breakoutbuddy/" in s or "/breakout_buddy/" in s or "/bb/" in s:
        return "BB"
    return os.getenv("CSV_SHIM_APP_DEFAULT", "BB")

def _table_from_path(path_like: Any) -> tuple[str, str] | None:
    try:
        p = Path(path_like)
    except Exception:
        return None
    if p.suffix.lower() != ".csv":
        return None
    app = _guess_app(p)
    parts = p.as_posix().lower().strip("/").split("/")[-4:]
    base = _VALID.sub("_", "_".join(parts[:-1] + [p.stem]))
    base = re.sub(r"__+", "_", base).strip("_") or "untitled"
    return app, f"{app}/{base}.parquet"

# --------- patch pandas ---------
_ORIG_READ_CSV = pd.read_csv
_ORIG_TO_CSV = pd.DataFrame.to_csv

def _read_csv(path_or_buf, *args, **kwargs):
    mapping = _table_from_path(path_or_buf)
    if not mapping:
        return _ORIG_READ_CSV(path_or_buf, *args, **kwargs)
    app, obj = mapping
    raw = _sb_download_bytes(obj)
    if not raw:
        # Nothing persisted yet → empty DF (caller should compute then save)
        return pd.DataFrame()
    try:
        import io
        return pd.read_parquet(io.BytesIO(raw))
    except Exception:
        # If parquet fails for any reason, fall back to original csv read
        return _ORIG_READ_CSV(path_or_buf, *args, **kwargs)

def _to_csv(self: pd.DataFrame, path_or_buf=None, *args, **kwargs):
    mapping = _table_from_path(path_or_buf) if path_or_buf is not None else None
    if not mapping:
        return _ORIG_TO_CSV(self, path_or_buf, *args, **kwargs)
    app, obj = mapping
    try:
        import io
        buf = io.BytesIO()
        self.to_parquet(buf, index=False)
        _sb_upload_bytes(obj, buf.getvalue())
        # Optional: also write locally by uncommenting next line
        # return _ORIG_TO_CSV(self, path_or_buf, *args, **kwargs)
        return None
    except Exception:
        # On failure, try local write to avoid breaking the app
        return _ORIG_TO_CSV(self, path_or_buf, *args, **kwargs)

# Activate
pd.read_csv = _read_csv
pd.DataFrame.to_csv = _to_csv
