from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# utilities/oracle_data.py
import json
import math
import time
import datetime as dt
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List
import urllib.request, urllib.error
import ssl

# Allow HTTPS on older boxes
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

ROOT = Path(__file__).resolve().parents[1]  # .../programs
DATA = ROOT / "Data"
CACHE = DATA / "oracle_cache.json"
CACHE.parent.mkdir(parents=True, exist_ok=True)

# --------------------- Moon phase (offline) ---------------------
# Simple but decent approximation (error < ~0.5 day)
# Source: adapts Conway/Chapront approximations
def _julian_date(d: dt.date) -> float:
    y, m, day = d.year, d.month, d.day
    if m <= 2:
        y -= 1
        m += 12
    A = y // 100
    B = 2 - A + (A // 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + day + B - 1524.5

def moon_phase_fraction(date: dt.date) -> float:
    # Reference new moon: 2000-01-06 18:14 UT (JD 2451550.1)
    jd = _julian_date(date)
    synodic = 29.53058867
    phase = (jd - 2451550.1) / synodic
    phase = phase - math.floor(phase)
    return float(phase)  # 0=new, 0.5=full

def moon_phase_bucket(date: dt.date) -> str:
    p = moon_phase_fraction(date)
    if p < 0.03 or p > 0.97:
        return "new"
    if 0.47 <= p <= 0.53:
        return "full"
    if p < 0.5:
        return "waxing"
    return "waning"

# --------------------- HTTP helpers ---------------------
def _http_json(url: str, timeout: int = 6) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AstroLotto/1.0 (+local app)",
            "Accept": "application/json,text/csv;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        ct = resp.headers.get("Content-Type","")
        raw = resp.read()
        # If CSV, delegate to CSV parser elsewhere
        return json.loads(raw.decode("utf-8", errors="ignore"))

def _http_text(url: str, timeout: int = 6) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AstroLotto/1.0 (+local app)", "Accept": "*/*"},
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def _load_cache() -> Dict[str, Any]:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_cache(data: Dict[str, Any]) -> None:
    try:
        CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

def _cached(key: str, ttl_seconds: int) -> Optional[Any]:
    now = time.time()
    cache = _load_cache()
    if key in cache:
        item = cache[key]
        if isinstance(item, dict) and "ts" in item and (now - float(item["ts"])) < ttl_seconds:
            return item.get("value")
    return None

def _put_cache(key: str, value: Any) -> Any:
    cache = _load_cache()
    cache[key] = {"ts": time.time(), "value": value}
    _save_cache(cache)
    return value

# --------------------- Space weather (NOAA SWPC) ---------------------
def kp_index_recent() -> Optional[float]:
    """
    Returns the most recent planetary Kp index (0..9) or None.
    Uses SWPC JSON endpoints with caching (10 minutes).
    """
    c = _cached("kp_index_recent", ttl_seconds=600)
    if c is not None:
        return c
    endpoints = [
        # 1-minute resolution, recent history
        "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json",
        # fallback daily 3‑hour indices
        "https://services.swpc.noaa.gov/json/planetary_k_index_1d.json",
    ]
    for url in endpoints:
        try:
            data = _http_json(url)
            if isinstance(data, list) and data:
                # Find last record with kp_index or kp value
                for row in reversed(data):
                    for k in ("kp_index","kp","Kp","kp_estimated"):
                        if k in row:
                            val = row[k]
                            try:
                                v = float(val)
                                if 0 <= v <= 9.9:
                                    return _put_cache("kp_index_recent", round(v, 1))
                            except Exception:
                                continue
        except Exception:
            continue
    return None

def solar_flare_activity(hours: int = 72) -> Dict[str, int]:
    """
    Returns {'M': m_count, 'X': x_count} for the last `hours` (default 72).
    Cached for 30 minutes. Best-effort against a few SWPC endpoints.
    """
    ck = f"solar_flare_{hours}h"
    c = _cached(ck, ttl_seconds=1800)
    if c is not None:
        return c

    now = dt.datetime.utcnow()
    start = now - dt.timedelta(hours=hours)
    counts = {"M": 0, "X": 0}
    endpoints = [
        # GOES X-ray events (primary); sometimes minutes-level granularity
        "https://services.swpc.noaa.gov/json/goes/primary/xray_flares_6h.json",
        "https://services.swpc.noaa.gov/json/goes/primary/xray_flares_24h.json",
        # Legacy flare list (bigger window)
        "https://services.swpc.noaa.gov/json/solar_flares.json",
    ]
    for url in endpoints:
        try:
            data = _http_json(url)
            if not isinstance(data, list):
                continue
            for row in data:
                # Try a handful of field names for class and time
                flare_class = None
                for k in ("flr_class","class","flare_class","xray_class","xray_classification","xray_class_abr"):
                    if k in row:
                        flare_class = str(row[k]).upper()
                        break
                tstr = None
                for tk in ("begin_time","event_time","time_tag","time_obs","start_time"):
                    if tk in row:
                        tstr = str(row[tk])
                        break
                if not flare_class or not tstr:
                    continue
                # Parse time (very tolerant)
                try:
                    t = dt.datetime.fromisoformat(tstr.replace("Z","+00:00"))
                except Exception:
                    try:
                        t = dt.datetime.strptime(tstr[:19], "%Y-%m-%dT%H:%M:%S")
                    except Exception:
                        continue
                if t.tzinfo is not None:
                    t = t.astimezone(dt.timezone.utc).replace(tzinfo=None)
                if t < start:
                    continue
                # Count by leading letter (A/B/C/M/X)
                lead = flare_class.strip()[:1]
                if lead in ("M","X"):
                    counts[lead] += 1
        except Exception:
            continue

    return _put_cache(ck, counts)

# --------------------- Markets (VIX proxy) ---------------------
def market_volatility_proxy(days: int = 5) -> Optional[float]:
    """
    Returns most recent VIX close (as float) via Yahoo Finance chart JSON.
    Cached for 30 minutes.
    """
    c = _cached("vix_proxy", ttl_seconds=1800)
    if c is not None:
        return c
    # Yahoo chart endpoint for ^VIX
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?range={max(days,1)}d&interval=1d"
    try:
        data = _http_json(url)
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None
        r0 = result[0]
        closes = r0.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        if closes:
            last = [x for x in closes if isinstance(x, (int, float))]
            if last:
                val = float(last[-1])
                return _put_cache("vix_proxy", round(val, 2))
    except Exception:
        pass
    return None

# --------------------- Admin/Test helpers ---------------------
def oracle_health() -> Dict[str, Any]:
    """Return a quick snapshot of current oracle inputs (without forcing refresh)."""
    today = dt.date.today()
    return {
        "moon": {
            "phase_bucket": moon_phase_bucket(today),
            "illum_pct": round(moon_phase_fraction(today) * 100, 1),
        },
        "kp_index_recent": kp_index_recent(),
        "solar_flares_72h": solar_flare_activity(72),
        "vix_proxy": market_volatility_proxy(),
    }

def refresh_oracle_now() -> Dict[str, Any]:
    """Force-refresh all online oracle signals and return them."""
    # Evict cache by writing new values
    k = kp_index_recent()
    fl = solar_flare_activity(72)
    v = market_volatility_proxy()
    return {"kp_index_recent": k, "solar_flares_72h": fl, "vix_proxy": v}
