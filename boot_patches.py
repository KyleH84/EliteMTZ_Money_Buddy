# boot_patches.py — safe, minimal tweaks to keep cloud/runtime stable without touching your app code.
from __future__ import annotations
import os, sys, time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
APP_ROOT = PROJECT_DIR / "EliteMTZ_Money_Buddy"

# Environment sanity
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("NUMEXPR_MAX_THREADS", "8")
os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("JAVA_TOOL_OPTIONS", "-Dfile.encoding=UTF-8")

# Ensure data & assets exist
(APP_ROOT / "data").mkdir(parents=True, exist_ok=True)
(APP_ROOT / "assets").mkdir(parents=True, exist_ok=True)

# Path safety
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

# Network hardening with retries/timeouts where libraries allow it
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    class _RetryingSession(requests.Session):
        def __init__(self):
            super().__init__()
            retries = Retry(
                total=3,
                connect=3,
                read=3,
                backoff_factor=0.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(["GET","POST","PUT","DELETE","HEAD","OPTIONS","PATCH"]),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retries, pool_connections=8, pool_maxsize=8)
            self.mount("http://", adapter)
            self.mount("https://", adapter)

    _session = _RetryingSession()

    _orig_request = requests.request
    def _patched_request(method, url, **kwargs):
        # default timeout if not set
        kwargs.setdefault("timeout", (5, 15))
        # forward to session so retries apply
        return _session.request(method, url, **kwargs)

    requests.request = _patched_request  # type: ignore
except Exception:
    pass

# yfinance wrapper for resilience (if present)
try:
    import yfinance as yf
    _orig_download = yf.download
    def _dl_wrap(*args, **kwargs):
        # sane defaults
        kwargs.setdefault("threads", True)
        kwargs.setdefault("auto_adjust", True)
        kwargs.setdefault("progress", False)
        try:
            return _orig_download(*args, **kwargs)
        except Exception:
            # second attempt: smaller interval
            kwargs["interval"] = "1d"
            return _orig_download(*args, **kwargs)
    yf.download = _dl_wrap  # type: ignore
except Exception:
    pass

# Pandas CSV gentle defaults (encoding issues crop up in the wild)
try:
    import pandas as pd
    _orig_read_csv = pd.read_csv
    def _read_csv_wrap(*args, **kwargs):
        kwargs.setdefault("encoding", "utf-8")
        kwargs.setdefault("on_bad_lines", "skip")
        return _orig_read_csv(*args, **kwargs)
    pd.read_csv = _read_csv_wrap  # type: ignore
except Exception:
    pass
