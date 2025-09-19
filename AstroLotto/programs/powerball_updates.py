
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List
import pandas as pd, re

@dataclass
class UpdateResult:
    draws_added: int
    jackpot_text: Optional[str]
    source_used: str

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df
    df.columns = [c.strip().lower() for c in df.columns]
    # unify special column name
    for cand in ("powerball", "pb", "special"):
        if cand in df.columns:
            df["powerball"] = pd.to_numeric(df[cand], errors="coerce").astype("Int64")
            break
    if "draw_date" in df.columns:
        df["draw_date"] = pd.to_datetime(df["draw_date"], errors="coerce")
    for c in ("white1","white2","white3","white4","white5"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    # clamp to legal ranges
    for c in ("white1","white2","white3","white4","white5"):
        if c in df.columns:
            df.loc[(df[c] < 1) | (df[c] > 69), c] = pd.NA
    if "powerball" in df.columns:
        df.loc[(df["powerball"] < 1) | (df["powerball"] > 26), "powerball"] = pd.NA
    return df

def _read_cache(cache_path: Path) -> pd.DataFrame:
    if cache_path.exists():
        try:
            return _normalize_df(pd.read_csv(cache_path))
        except Exception:
            pass
    return pd.DataFrame()

def _write_cache(cache_path: Path, df: pd.DataFrame) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        df.to_csv(cache_path, index=False); return
    df_sorted = df.sort_values("draw_date").drop_duplicates(subset=["draw_date"], keep="last")
    df_sorted.to_csv(cache_path, index=False)

def _safe_requests_bs4():
    try:
        import requests
        from bs4 import BeautifulSoup
        return requests, BeautifulSoup
    except Exception:
        return None, None

def fetch_primary(url: str) -> Tuple[pd.DataFrame, Optional[str], str]:
    requests, BeautifulSoup = _safe_requests_bs4()
    if not requests: return pd.DataFrame(), None, "no-requests"
    try:
        headers = {"User-Agent": "AstroLotto/1.0"}
        r = requests.get(url, headers=headers, timeout=20); r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        records: List[dict] = []
        # generic scrape: find rows with date + numbers
        for tr in soup.find_all("tr"):
            cols = [c.get_text(" ", strip=True) for c in tr.find_all(["td","th"])]
            if len(cols) < 3: 
                continue
            dt = None
            for fmt in ("%b %d, %Y", "%m/%d/%Y"):
                try:
                    dt = datetime.strptime(cols[0], fmt); break
                except Exception:
                    pass
            if not dt: 
                continue
            nums = [int(x) for x in re.findall(r"\b\d{1,2}\b", " ".join(cols[1:]))]
            if len(nums) >= 6:
                row = {"draw_date": dt, "white1": nums[0], "white2": nums[1], "white3": nums[2], "white4": nums[3], "white5": nums[4], "powerball": nums[5]}
                records.append(row)
        jp = None
        jpn = soup.find(string=re.compile("Jackpot", re.I))
        if jpn:
            try:
                jp = " ".join(jpn.parent.get_text(" ", strip=True).split())
            except Exception:
                pass
        return _normalize_df(pd.DataFrame(records)), jp, url
    except Exception:
        return pd.DataFrame(), None, "fetch-failed"

def update_powerball(root: Path) -> UpdateResult:
    cache_path = root / "Data" / "cached_powerball_data.csv"
    current = _read_cache(cache_path); last_count = len(current)
    df, jp, src = fetch_primary("https://www.lotteryusa.com/powerball/")
    if not df.empty:
        import pandas as pd
        merged = pd.concat([current, df], ignore_index=True)
        merged = _normalize_df(merged); _write_cache(cache_path, merged)
        return UpdateResult(draws_added=len(merged)-last_count, jackpot_text=jp, source_used=src)
    # no data fetched; keep existing cache untouched
    return UpdateResult(draws_added=0, jackpot_text=None, source_used="none")
