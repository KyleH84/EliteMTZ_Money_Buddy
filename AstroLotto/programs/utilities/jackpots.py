from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# utilities/jackpots.py — live jackpot fetcher (cached + override)
from pathlib import Path
from typing import Optional, Dict, Any
import json, re, time

try:
    import requests
except Exception:
    requests = None

try:
    from bs4 import BeautifulSoup  # optional
except Exception:
    BeautifulSoup = None

ROOT = Path(".").resolve()
DATA = ROOT / "Data"
CACHE = DATA / "cache"
LOGS = DATA / "logs"
CACHE.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

CACHE_FILE = CACHE / "jackpots.json"
OVERRIDE_FILE = CACHE / "jackpots_override.json"

USER_AGENT = {"User-Agent": "Mozilla/5.0 (AstroLotto Jackpot Fetcher)"}

def _log(msg: str) -> None:
    try:
        (LOGS / "jackpots.log").open("a", encoding="utf-8").write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass

def _read_json(p: Path) -> Dict[str, Any]:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _write_json(p: Path, obj: Dict[str, Any]) -> None:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)
    except Exception as e:
        _log(f"write_json error {p}: {e}")

def _parse_usd(text: str) -> Optional[int]:
    # "$123 Million", "$1.2 Billion", "$123,000,000" -> int dollars
    if not text:
        return None
    s = text.replace(",", " ").replace("\xa0"," ").strip()
    m = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|m|b)?", s, re.I)
    if not m:
        # bare 123000000
        m2 = re.search(r"([0-9]{6,})", s)
        if m2:
            try: return int(m2.group(1))
            except (ValueError, TypeError):
                return None
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit in ("billion","b"):
        return int(round(num * 1_000_000_000))
    if unit in ("million","m"):
        return int(round(num * 1_000_000))
    return int(round(num))

# -------- Fetchers (best-effort + fallback to LotteryUSA) --------

def _fetch_powerball() -> Optional[int]:
    if requests is None:
        return None
    # Try official Powerball site text pattern
    try:
        r = requests.get("https://www.powerball.com/", headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        # Look for "$xxx Million" near 'Jackpot' text
        m = re.search(r"\$[0-9,\.]+\s*(?:Million|Billion)", r.text, re.I)
        if m:
            val = _parse_usd(m.group(0))
            if val: return val
    except Exception as e:
        _log(f"powerball official fail: {e}")
    # LotteryUSA fallback
    try:
        r = requests.get("https://www.lotteryusa.com/powerball/", headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        m = re.search(r"\$[0-9,\.]+\s*(?:Million|Billion)", r.text, re.I)
        if m:
            val = _parse_usd(m.group(0))
            if val: return val
    except Exception as e:
        _log(f"powerball lotteryusa fail: {e}")
    return None

def _fetch_megamillions() -> Optional[int]:
    if requests is None:
        return None
    # Try official Mega Millions site
    try:
        r = requests.get("https://www.megamillions.com/", headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        m = re.search(r"\$[0-9,\.]+\s*(?:Million|Billion)", r.text, re.I)
        if m:
            val = _parse_usd(m.group(0))
            if val: return val
    except Exception as e:
        _log(f"megamillions official fail: {e}")
    # LotteryUSA fallback
    try:
        r = requests.get("https://www.lotteryusa.com/megamillions/", headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        m = re.search(r"\$[0-9,\.]+\s*(?:Million|Billion)", r.text, re.I)
        if m:
            val = _parse_usd(m.group(0))
            if val: return val
    except Exception as e:
        _log(f"megamillions lotteryusa fail: {e}")
    return None

def _fetch_colorado() -> Optional[int]:
    if requests is None:
        return None
    # Colorado Lotto+ via LotteryUSA (official site is JS-heavy)
    try:
        r = requests.get("https://www.lotteryusa.com/colorado/lotto/", headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        m = re.search(r"\$[0-9,\.]+\s*(?:Million|Billion)", r.text, re.I)
        if m:
            val = _parse_usd(m.group(0))
            if val: return val
    except Exception as e:
        _log(f"colorado lotteryusa fail: {e}")
    return None

_FETCHERS = {
    "powerball": _fetch_powerball,
    "megamillions": _fetch_megamillions,
    "colorado": _fetch_colorado,
}

def get_jackpot(game: str, force_refresh: bool = False) -> Optional[int]:
    """Return current jackpot in dollars for game in {'powerball','megamillions','colorado'}.
       Uses overrides if present; caches successful fetches in Data/cache/jackpots.json
    """
    key = game.strip().lower()
    # Overrides first
    ov = _read_json(OVERRIDE_FILE)
    if key in ov:
        try: return int(ov[key])
        except Exception: pass

    cache = _read_json(CACHE_FILE)
    if (not force_refresh) and key in cache and "value" in cache[key] and (time.time() - float(cache[key].get("ts",0)) < 3*3600):
        try: return int(cache[key]["value"])
        except Exception: pass

    fetcher = _FETCHERS.get(key)
    if not fetcher:
        return None
    val = None
    try:
        val = fetcher()
    except Exception as e:
        _log(f"fetch error {key}: {e}")
        val = None

    # Update cache if we got a value
    if val:
        cache[key] = {"value": int(val), "ts": time.time()}
        _write_json(CACHE_FILE, cache)

    if val:
        return int(val)

    # Fallback: old cache
    if key in cache and "value" in cache[key]:
        try: return int(cache[key]["value"])
        except Exception: pass
    return None

def set_override(game: str, dollars: int) -> None:
    key = game.strip().lower()
    ov = _read_json(OVERRIDE_FILE)
    ov[key] = int(dollars)
    _write_json(OVERRIDE_FILE, ov)

def clear_override(game: str) -> None:
    key = game.strip().lower()
    ov = _read_json(OVERRIDE_FILE)
    if key in ov:
        del ov[key]
        _write_json(OVERRIDE_FILE, ov)
