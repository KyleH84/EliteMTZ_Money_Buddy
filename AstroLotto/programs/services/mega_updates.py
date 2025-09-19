from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import historical_backfill  # fallback to NY Open Data for full history
from typing import Optional, Tuple
import pandas as pd, re

@dataclass
class UpdateResult:
    draws_added: int
    jackpot_text: Optional[str]
    source_used: str

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy(); df.columns = [c.strip().lower() for c in df.columns]
    if "draw_date" in df.columns:
        try: df["draw_date"] = pd.to_datetime(df["draw_date"])
        except Exception: pass
    for i in range(1,6):
        col = f"white{i}"
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ("mega","bonus"):
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df

def _read_cache(cache_path: Path) -> pd.DataFrame:
    if cache_path.exists():
        try: return _normalize_df(pd.read_csv(cache_path))
        except Exception: pass
    return pd.DataFrame()

def _write_cache(cache_path: Path, df: pd.DataFrame) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df_sorted = df.sort_values("draw_date").drop_duplicates(subset=["draw_date"], keep="last")
    df_sorted.to_csv(cache_path, index=False)

def _safe_requests_bs4():
    try:
        import requests
        from bs4 import BeautifulSoup
        return requests, BeautifulSoup
    except Exception:
        return None, None

def fetch_official() -> Tuple[pd.DataFrame, Optional[str], str]:
    requests, BeautifulSoup = _safe_requests_bs4()
    if not requests: return pd.DataFrame(), None, "no-requests"
    try:
        url = "https://www.megamillions.com/Winning-Numbers/Previous-Drawings.aspx"
        headers = {"User-Agent":"AstroLotto/1.0"}
        r = requests.get(url, headers=headers, timeout=15); r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        records = []
        for tr in soup.select("tr"):
            cols = [c.get_text(strip=True) for c in tr.find_all(["td","th"])]
            if len(cols) < 7 or "DATE" in (cols[0].upper() if cols else ""): continue
            try: dt = datetime.strptime(cols[0], "%m/%d/%Y")
            except Exception: continue
            nums = re.findall(r"\d+", " ".join(cols[1:6]))
            if len(nums) < 6: continue
            white = [int(x) for x in nums[:5]]; mega = int(nums[5])
            jackpot = " ".join(cols[6].split()) if len(cols) >= 7 else None
            records.append({"draw_date":dt,"white1":white[0],"white2":white[1],"white3":white[2],"white4":white[3],"white5":white[4],"mega":mega,"jackpot":jackpot})
        jp = None; el = soup.select_one(".next-jackpot, .estimated-jackpot, .jackpot-amount")
        if el: jp = " ".join(el.get_text(" ", strip=True).split())
        return _normalize_df(pd.DataFrame(records)), jp, "official"
    except Exception:
        return pd.DataFrame(), None, "official-failed"

def fetch_lotteryusa() -> Tuple[pd.DataFrame, Optional[str], str]:
    requests, BeautifulSoup = _safe_requests_bs4()
    if not requests: return pd.DataFrame(), None, "no-requests"
    try:
        url = "https://www.lotteryusa.com/megamillions/"
        headers = {"User-Agent":"AstroLotto/1.0"}
        r = requests.get(url, headers=headers, timeout=15); r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        records = []
        for node in soup.find_all(True):
            txt = node.get_text(" ", strip=True)
            mdate = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", txt)
            if not mdate: continue
            try: dt = datetime.strptime(mdate.group(1), "%m/%d/%Y")
            except Exception: continue
            nums = [int(x) for x in re.findall(r"\b\d{1,2}\b", txt)]
            if len(nums) >= 6:
                white = nums[:5]; mega = nums[5]
                records.append({"draw_date":dt,"white1":white[0],"white2":white[1],"white3":white[2],"white4":white[3],"white5":white[4],"mega":mega})
        jp = None; jpn = soup.find(string=re.compile("Jackpot", re.I))
        if jpn: jp = " ".join(jpn.parent.get_text(" ", strip=True).split())
        return _normalize_df(pd.DataFrame(records)), jp, "lotteryusa"
    except Exception:
        return pd.DataFrame(), None, "lotteryusa-failed"

def update_megamillions(root: Path) -> UpdateResult:
    data_dir = root / "Data"; cache_path = data_dir / "cached_megamillions_data.csv"
    current = _read_cache(cache_path); last_count = len(current)
    # Try official then LotteryUSA
    for fetcher in (fetch_official, fetch_lotteryusa):
        try:
            df, jp, src = fetcher()
            if not df.empty:
                import pandas as pd
                merged = pd.concat([current, df], ignore_index=True)
                merged = _normalize_df(merged); _write_cache(cache_path, merged)
                return UpdateResult(draws_added=len(merged)-last_count, jackpot_text=jp, source_used=src)
        except Exception:
            continue
    # Fallback: NY Open Data historical backfill
    try:
        res = historical_backfill.ensure_history_csv(str(cache_path), game="megamillions")
        current2 = _read_cache(cache_path); now_count = len(current2)
        return UpdateResult(draws_added=max(0, now_count - last_count), jackpot_text=None, source_used="ny-open-data")
    except Exception:
        return UpdateResult(draws_added=0, jackpot_text=None, source_used="none")