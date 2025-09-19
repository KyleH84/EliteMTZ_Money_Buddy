# Live feeds + scaling used by oracle_autofill
from __future__ import annotations
import requests
from typing import Dict

CAP_TOTAL = 0.33
CAP_MARKETS = 0.12
CAP_SPACE = 0.07
CAP_WEIRD = 0.08

MARKETS_FULL_SCALE_CHANGE = 0.10
SPACE_FULL_SCALE_KP = 9.0
WEIRD_FULL_SCALE_COUNT = 80
WEIRD_FULL_SCALE_MAXMAG = 6.5

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _markets_part() -> float:
    try:
        r = requests.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
                         params={"vs_currency":"usd","days":"2"}, timeout=10)
        r.raise_for_status()
        prices = r.json().get("prices", [])
        if len(prices) < 2: return 0.0
        p0 = prices[0][1]; p1 = prices[-1][1]
        change = abs((p1 - p0) / p0)
        frac = _clip(change / MARKETS_FULL_SCALE_CHANGE, 0.0, 1.0)
        return frac * CAP_MARKETS
    except Exception:
        return 0.0

def _space_part() -> float:
    try:
        r = requests.get("https://services.swpc.noaa.gov/json/planetary_k_index_1m.json", timeout=10)
        r.raise_for_status()
        arr = r.json()[-180:]
        if not arr: return 0.0
        kp = [float(it.get("kp_index", 0)) for it in arr if "kp_index" in it]
        if not kp: return 0.0
        avg_k = sum(kp)/len(kp)
        frac = _clip(avg_k / SPACE_FULL_SCALE_KP, 0.0, 1.0)
        return frac * CAP_SPACE
    except Exception:
        return 0.0

def _weird_part() -> float:
    try:
        r = requests.get("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson", timeout=10)
        r.raise_for_status()
        feats = r.json().get("features", [])
        cnt = len(feats)
        maxmag = 0.0
        for f in feats[:500]:
            try:
                m = float(f["properties"].get("mag") or 0.0)
                if m > maxmag: maxmag = m
            except Exception:
                pass
        frac_count = _clip(cnt / WEIRD_FULL_SCALE_COUNT, 0.0, 1.0)
        frac_mag = _clip(max(0.0, (maxmag - 4.0)) / max(0.1, (WEIRD_FULL_SCALE_MAXMAG - 4.0)), 0.0, 1.0)
        return (0.5*frac_count + 0.5*frac_mag) * CAP_WEIRD
    except Exception:
        return 0.0

def get_live_parts() -> Dict[str, float]:
    return {
        "markets": float(_markets_part()),
        "space": float(_space_part()),
        "weird": float(_weird_part()),
        "cap": CAP_TOTAL,
    }
