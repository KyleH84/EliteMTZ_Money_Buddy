# Jackpots fetcher with caching + override
from __future__ import annotations
from pathlib import Path
import json, re, time
from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Data"
CACHE_DIR = DATA / "cache"
LOGS_DIR = DATA / "logs"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

CACHE_FILE = CACHE_DIR / "jackpots.json"
OVERRIDE_FILE = DATA / "jackpots_override.json"

USER_AGENT = {"User-Agent":"Mozilla/5.0 (compatible; AstroLotto/1.0)"}

def _log(msg: str):
    try:
        (LOGS_DIR / "jackpots.log").write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n", encoding="utf-8", append=True)
    except Exception:
        with (LOGS_DIR / "jackpots.log").open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")

def _read_json(p: Path) -> Dict[str, Any]:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _write_json(p: Path, obj: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)

def _parse_usd(text: str) -> Optional[int]:
    # Extract numbers like $123 Million, $1.2 Billion, 123,000,000
    s = text.replace(",", "").strip()
    m = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|m|b)?", s, re.I)
    if not m:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit in ("billion","b"):
        return int(round(num * 1_000_000_000))
    if unit in ("million","m"):
        return int(round(num * 1_000_000))
    # plain dollars
    return int(round(num))

# --- Fetchers ---
def fetch_megamillions() -> Optional[int]:
    # Try official page first
    try:
        r = requests.get("https://www.megamillions.com/Winning-Numbers.aspx", headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        # Look for jackpot text
        for el in soup.find_all(True, text=True):
            t = el.get_text(" ", strip=True)
            if "jackpot" in t.lower():
                val = _parse_usd(t)
                if val and val > 0:
                    return val
    except Exception:
        pass
    # Fallback: lotteryusa
    try:
        r = requests.get("https://www.lotteryusa.com/megamillions/", headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        m = re.search(r"(\$[0-9,\.]+\s*(million|billion)?)", r.text, re.I)
        if m:
            val = _parse_usd(m.group(0))
            if val and val > 0:
                return val
    except Exception:
        pass
    return None

def fetch_colorado_lotto() -> Optional[int]:
    # Colorado Lotto+ official
    try:
        r = requests.get("https://www.coloradolottery.com/en/games/lotto-plus/", headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        # Look for 'Estimated Jackpot'
        text = soup.get_text(" ", strip=True)
        m = re.search(r"(Estimated\s+Jackpot[^$]*\$[0-9,\.]+\s*(million|billion)?)", text, re.I)
        if m:
            val = _parse_usd(m.group(0))
            if val and val > 0:
                return val
    except Exception:
        pass
    # Fallback: lotteryusa
    try:
        r = requests.get("https://www.lotteryusa.com/colorado/lotto/", headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        m = re.search(r"(\$[0-9,\.]+\s*(million|billion)?)", r.text, re.I)
        if m:
            val = _parse_usd(m.group(0))
            if val and val > 0:
                return val
    except Exception:
        pass
    return None

def fetch_powerball() -> Optional[int]:
    try:
        r = requests.get("https://www.powerball.com/", headers=USER_AGENT, timeout=10)
        r.raise_for_status()
        m = re.search(r"(\$[0-9,\.]+\s*(million|billion)?)", r.text, re.I)
        if m:
            return _parse_usd(m.group(0))
    except Exception:
        pass
    return None

FETCHERS = {
    "powerball": fetch_powerball,
    "megamillions": fetch_megamillions,
    "colorado": fetch_colorado_lotto,
}

def get_jackpot(game: str, force_refresh: bool=False) -> Optional[int]:
    game = game.lower().strip()
    overrides = _read_json(OVERRIDE_FILE)
    if game in overrides and not force_refresh:
        return overrides.get(game)
    cache = _read_json(CACHE_FILE)
    now = time.time()
    cached = cache.get(game, {})
    if cached and not force_refresh and (now - cached.get("ts", 0)) < 6*3600:
        return cached.get("value")
    # fetch
    fn = FETCHERS.get(game)
    value = None
    if fn:
        try:
            value = fn()
        except Exception as e:
            _log(f"[{game}] fetch error: {e}")
    if value:
        cache[game] = {"value": int(value), "ts": now}
        _write_json(CACHE_FILE, cache)
    return value or cached.get("value")

def set_override(game: str, dollars: int) -> None:
    game = game.lower().strip()
    overrides = _read_json(OVERRIDE_FILE)
    overrides[game] = int(dollars)
    _write_json(OVERRIDE_FILE, overrides)

def clear_override(game: str) -> None:
    game = game.lower().strip()
    overrides = _read_json(OVERRIDE_FILE)
    if game in overrides:
        del overrides[game]
        _write_json(OVERRIDE_FILE, overrides)
