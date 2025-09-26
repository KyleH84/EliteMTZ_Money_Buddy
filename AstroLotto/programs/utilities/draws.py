from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


# utilities/draws.py - v10.3.6 (robust providers + fallbacks)
import csv, os, re
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional
import requests
import pandas as pd
from bs4 import BeautifulSoup

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "AstroLotto/10.3.6 (+https://local)"})
TIMEOUT = 20

NYOD_POWERBALL = "https://data.ny.gov/resource/d6yy-54nr.json?$order=draw_date%20ASC&$limit=50000"
NYOD_MEGAMILLIONS = "https://data.ny.gov/resource/5xaw-6ayf.json?$order=draw_date%20ASC&$limit=50000"

CO_MONTH_URLS = {
    "colorado_lottery": "https://www.coloradolottery.com/en/games/lotto/drawings/{year}-{month:02d}/",
    "cash5":            "https://www.coloradolottery.com/en/games/cash5/drawings/{year}-{month:02d}/",
    "pick3":            "https://www.coloradolottery.com/en/games/pick3/drawings/{year}-{month:02d}/",
    "lucky_for_life":   "https://www.coloradolottery.com/en/games/luckyforlife/drawings/{year}-{month:02d}/",
}

LNET_POWERBALL = "https://www.lottery.net/powerball/numbers"
LNET_MEGAMILLIONS = "https://www.lottery.net/mega-millions/numbers"

LUSA_PAGES = {
    "powerball": "https://www.lotteryusa.com/powerball/",
    "mega_millions": "https://www.lotteryusa.com/mega-millions/",
    "lucky_for_life": "https://www.lotteryusa.com/lucky-for-life/",
    "colorado_lottery": "https://www.lotteryusa.com/colorado/lotto/",
    "cash5": "https://www.lotteryusa.com/colorado/cash-5/",
    "pick3": "https://www.lotteryusa.com/colorado/pick-3/",
}

def _fmt(d: date) -> str:
    return d.strftime("%m/%d/%Y")

def _parse_date(s: str) -> Optional[date]:
    if not s: return None
    s = s.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%y", "%A, %B %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None

def _read_csv(csv_path: str) -> List[Dict[str,str]]:
    try:
        return pd.read_csv(csv_path, dtype=str).fillna("").to_dict(orient="records")
    except FileNotFoundError:
        return []
    except Exception:
        rows = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    rows.append({k: (v or "") for k,v in r.items()})
        except Exception:
            pass
        return rows

def _write_csv(csv_path: str, rows: List[Dict[str,str]], fieldnames: List[str]):
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

def _nums(text: str):
    return [int(x) for x in re.findall(r"\b\d+\b", text or "")]

def _nyod_powerball() -> List[Dict[str,str]]:
    r = SESSION.get(NYOD_POWERBALL, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for row in data:
        dt = row.get("draw_date") or row.get("draw_date_est")
        from datetime import datetime as _dt
        d = _parse_date(dt)
        if not d and dt:
            # try trimming time part like "2024-07-17T00:00:00.000"
            try:
                d = _dt.fromisoformat(dt.replace("Z","").split("T")[0]).date()
            except Exception:
                d = None
        if not d: continue
        wn = (row.get("winning_numbers") or "").replace(",", " ").split()
        if len(wn) < 6: continue
        rec = {"date": _fmt(d)}
        for i in range(5): rec[f"n{i+1}"] = wn[i]
        rec["s1"] = wn[5]
        out.append(rec)
    return out

def _nyod_megamillions() -> List[Dict[str,str]]:
    r = SESSION.get(NYOD_MEGAMILLIONS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for row in data:
        dt = row.get("draw_date")
        d = _parse_date(dt)
        if not d: continue
        wn = (row.get("winning_numbers") or "").replace(",", " ").split()
        if len(wn) < 6: continue
        rec = {"date": _fmt(d)}
        for i in range(5): rec[f"n{i+1}"] = wn[i]
        rec["s1"] = wn[5]
        out.append(rec)
    return out

def _lnet_collect(base_url: str, expected_white: int) -> List[Dict[str,str]]:
    r = SESSION.get(base_url, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    out = []
    for block in soup.select("div.results, div.result, li, article"):
        t = block.get_text(" ", strip=True)
        d = None
        for el in block.find_all(["time","h3","h4","h2","span"]):
            d = d or _parse_date(el.get_text(strip=True))
        if not d:
            import re as _re
            m = _re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}", t)
            if m: d = _parse_date(m.group(0))
        arr = _nums(t)
        if d and len(arr) >= expected_white:
            rec = {"date": _fmt(d)}
            for i in range(expected_white):
                rec[f"n{i+1}"] = str(arr[i])
            if len(arr) > expected_white:
                rec["s1"] = str(arr[expected_white])
            out.append(rec)
    uniq = {r["date"]: r for r in out}
    return [uniq[k] for k in sorted(uniq.keys(), key=lambda s: datetime.strptime(s, "%m/%d/%Y").date())]

def _co_month(url_tmpl: str, year: int, month: int) -> List[Tuple[date, List[int]]]:
    url = url_tmpl.format(year=year, month=month)
    r = SESSION.get(url, timeout=TIMEOUT)
    if r.status_code >= 400:
        return []
    soup = BeautifulSoup(r.text, "lxml")
    out = []
    for li in soup.select("div.drawing, li, article, div.card-item"):
        t = li.get_text(" ", strip=True)
        if "number" not in t.lower():
            continue
        d = None
        for el in li.find_all(["time","span","p","h3","h4"]):
            d = d or _parse_date(el.get_text(strip=True))
        if not d:
            import re as _re
            m = _re.search(r"(\d{1,2}/\d{1,2}/\d{2,4}|[A-Za-z]+\s+\d{1,2},\s+\d{4})", t)
            if m: d = _parse_date(m.group(0))
        arr = _nums(t)
        if d and arr:
            out.append((d, arr))
    uniq = {}
    for d, arr in out:
        uniq[d] = arr
    return sorted(uniq.items(), key=lambda x: x[0])

def _fetch_co_game(game: str, years_back: int) -> List[Dict[str,str]]:
    meta = {
        "colorado_lottery": (CO_MONTH_URLS["colorado_lottery"], 6, False),
        "cash5":            (CO_MONTH_URLS["cash5"], 5, False),
        "pick3":            (CO_MONTH_URLS["pick3"], 3, False),
        "lucky_for_life":   (CO_MONTH_URLS["lucky_for_life"], 5, True),
    }[game]
    tmpl, white_count, has_special = meta
    from datetime import date as _date
    today = _date.today()
    out_rows, seen = [], set()
    months = years_back * 12 + 2
    y, m = today.year, today.month
    for _ in range(months):
        rows = _co_month(tmpl, y, m)
        for d, balls in rows:
            if d in seen: 
                continue
            rec = {"date": _fmt(d)}
            for i in range(white_count):
                rec[f"n{i+1}"] = str(balls[i]) if i < len(balls) else ""
            if has_special:
                rec["s1"] = str(balls[white_count]) if len(balls) > white_count else ""
            out_rows.append(rec); seen.add(d)
        m -= 1
        if m == 0: m = 12; y -= 1
    out_rows.sort(key=lambda r: datetime.strptime(r["date"], "%m/%d/%Y").date())
    return out_rows

def _lusa_table(game_key: str) -> List[Dict[str,str]]:
    url = LUSA_PAGES.get(game_key)
    if not url: return []
    r = SESSION.get(url, timeout=TIMEOUT)
    if r.status_code >= 400:
        return []
    soup = BeautifulSoup(r.text, "lxml")
    table = soup.select_one("table.drawings") or soup.find("table")
    if not table: return []
    out = []
    for tr in table.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 2: continue
        d = _parse_date(tds[0].get_text(strip=True))
        if not d: continue
        arr = _nums(tds[1].get_text(" ", strip=True))
        rec = {"date": _fmt(d)}
        for i in range(min(6, len(arr))):
            if i < 5:
                rec[f"n{i+1}"] = str(arr[i])
            elif len(arr) >= 6:
                rec["s1"] = str(arr[5])
        out.append(rec)
    uniq = {r["date"]: r for r in out}
    return [uniq[k] for k in sorted(uniq.keys(), key=lambda s: datetime.strptime(s, "%m/%d/%Y").date())]

def update_draws_since_last(game_key: str, csv_path: str, years_back: int = 5) -> int:
    existing = _read_csv(csv_path)
    by_date = {r.get("date"): r for r in existing if r.get("date")}
    fetched: List[Dict[str,str]] = []

    try:
        if game_key == "powerball":
            fetched = _nyod_powerball()
        elif game_key == "mega_millions":
            fetched = _nyod_megamillions()
        elif game_key in ("colorado_lottery", "cash5", "pick3", "lucky_for_life"):
            fetched = _fetch_co_game(game_key, years_back)
    except Exception:
        fetched = []

    if not fetched:
        try:
            if game_key == "powerball":
                fetched = _lnet_collect(LNET_POWERBALL, expected_white=5)
            elif game_key == "mega_millions":
                fetched = _lnet_collect(LNET_MEGAMILLIONS, expected_white=5)
        except Exception:
            fetched = fetched or []

    if not fetched:
        try:
            fetched = _lusa_table(game_key)
        except Exception:
            fetched = fetched or []

    if not fetched:
        return 0

    merged = dict(by_date)
    for r in fetched:
        if r.get("date"):
            merged[r["date"]] = r

    sample = merged[next(iter(merged))]
    white_count = max([int(k[1:]) for k in sample.keys() if k.startswith("n")] + [0])
    has_special = "s1" in sample
    fields = ["date"] + [f"n{i+1}" for i in range(white_count)]
    if has_special: fields.append("s1")

    rows_sorted = [merged[d] for d in sorted(merged.keys(), key=lambda s: datetime.strptime(s, "%m/%d/%Y").date())]
    _write_csv(csv_path, rows_sorted, fields)

    new_count = sum(1 for d in merged if d not in by_date)
    return int(new_count)
