from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# utilities/qrng.py
import os, time, hashlib, json
from typing import Optional
try:
    import requests
except Exception:
    requests = None

def qrng_seed(api_key: Optional[str] = None, fallback_entropy: Optional[str] = None) -> int:
    url = "https://qrng.anu.edu.au/API/jsonI.php?length=8&type=uint16"
    try:
        if requests is not None:
            r = requests.get(url, timeout=5)
            if r.ok:
                js = r.json()
                if js.get("success") and js.get("data"):
                    vals = js["data"]
                    payload = json.dumps(vals).encode("utf-8")
                    h = hashlib.sha256(payload).hexdigest()
                    return int(h[:16], 16)
    except Exception:
        pass
    salt = (fallback_entropy or "") + str(time.time_ns()) + os.getenv("HOSTNAME","")
    h = hashlib.sha256(salt.encode("utf-8")).hexdigest()
    return int(h[:16], 16)
