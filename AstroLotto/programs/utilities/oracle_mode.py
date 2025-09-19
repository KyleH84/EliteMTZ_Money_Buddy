# Program/utilities/oracle_mode.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional
from pathlib import Path
import json, datetime as dt

MAX_CHAOS_TOTAL = 0.30
MAX_SCORE_BIAS = 0.12

@dataclass
class OracleSettings:
    use_moon: bool = True
    use_markets: bool = True
    use_space: bool = True
    use_weird: bool = False
    user_sign: Optional[str] = None

def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def load_feeds(project_root: Path) -> dict:
    feeds_dir = project_root / "Data" / "feeds"
    return {
        "moon": _load_json(feeds_dir / "moon.json"),
        "markets": _load_json(feeds_dir / "markets.json"),
        "space": _load_json(feeds_dir / "space_weather.json"),
        "flags": _load_json(feeds_dir / "weird_flags.json"),
    }

def chaos_from_moon(date: dt.date, feeds: dict) -> float:
    rec = (feeds.get("moon") or {}).get(date.isoformat())
    illum = float(rec.get("illum", 0.0)) if rec else 0.0
    val = 0.12 * (illum ** 1.25)
    return max(0.0, min(val, 0.12))

def chaos_from_markets(date: dt.date, feeds: dict) -> float:
    rec = (feeds.get("markets") or {}).get(date.isoformat()) or {}
    btc = abs(float(rec.get("btc_pct", 0.0)))
    spx = abs(float(rec.get("spx_pct", 0.0)))
    vol = min(max(btc, spx), 8.0) / 8.0
    return min(0.10 * vol, 0.10)

def chaos_from_space(date: dt.date, feeds: dict) -> float:
    rec = (feeds.get("space") or {}).get(date.isoformat()) or {}
    kp = float(rec.get("kp", 0.0))
    return min(0.15 * (kp / 9.0) ** 1.1, 0.15)

def chaos_from_weird(date: dt.date, feeds: dict) -> float:
    rec = (feeds.get("flags") or {}).get(date.isoformat()) or {}
    return 0.08 if rec.get("weird") else 0.0

def _combine(parts):
    x = 1.0
    for p in parts:
        p = max(0.0, min(1.0, float(p)))
        x *= (1.0 - p)
    return 1.0 - x

_SIGN_BUCKETS = {
    "aries": [(1,10)], "taurus": [(11,20)], "gemini": [(21,30)],
    "cancer": [(31,40)], "leo": [(41,50)], "virgo": [(51,60)],
    "libra": [(61,70)], "scorpio": [(1,10)], "sagittarius": [(11,20)],
    "capricorn": [(21,30)], "aquarius": [(31,40)], "pisces": [(41,50)],
}

def score_bias_for_sign(user_sign: Optional[str], lo: int, hi: int, impact: float) -> Dict[int, float]:
    if not user_sign:
        return {}
    sign = user_sign.lower().strip()
    ranges = _SIGN_BUCKETS.get(sign, [])
    if not ranges:
        return {}
    mag = min(MAX_SCORE_BIAS * impact, MAX_SCORE_BIAS)
    bias: Dict[int,float] = {}
    for n in range(lo, hi+1):
        bump = 0.0
        for (a,b) in ranges:
            if a <= ((n - lo) % 70) + 1 <= b:
                bump = mag
                break
        bias[n] = 1.0 + bump
    return bias

def compute_oracle(draw_date: dt.date, lo: int, hi: int, settings: OracleSettings, feeds: dict) -> dict:
    moon = chaos_from_moon(draw_date, feeds) if settings.use_moon else 0.0
    market = chaos_from_markets(draw_date, feeds) if settings.use_markets else 0.0
    space = chaos_from_space(draw_date, feeds) if settings.use_space else 0.0
    weird = chaos_from_weird(draw_date, feeds) if settings.use_weird else 0.0
    combined = min(_combine([moon, market, space, weird]), 0.30)
    score_mult = score_bias_for_sign(settings.user_sign, lo, hi, impact=(combined / 0.30) if 0.30>0 else 0.0)
    return {"chaos": combined, "parts": {"moon": moon, "markets": market, "space": space, "weird": weird}, "score_mult": score_mult}
