
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
    if df.empty: return df
    df.columns = [c.strip().lower() for c in df.columns]
    if "draw_date" in df.columns:
        # strip draw-time tokens and reparse robustly
        s = df["draw_date"].astype(str).str.replace(r"(?i)\b(midday|evening|mid\s*day)\b", "", regex=True).str.strip()
        df["draw_date"] = pd.to_datetime(s, errors="coerce", infer_datetime_format=True)
    for c in ("white1","white2","white3"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
            df.loc[(df[c] < 0) | (df[c] > 9), c] = pd.NA
    return df

def _read_cache(cache_path: Path) -> pd.DataFrame:
    if cache_path.exists():
        try: return _normalize_df(pd.read_csv(cache_path))
        except Exception: pass
    return pd.DataFrame()

def _write_cache(cache_path: Path, df: pd.DataFrame) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        df.to_csv(cache_path, index=False); return
    if "draw_date" in df.columns:
        df = df.dropna(subset=["draw_date"])
    df_sorted = df.sort_values("draw_date").drop_duplicates(subset=["draw_date"], keep="last")
    df_sorted.to_csv(cache_path, index=False)

def _safe_requests_bs4():
    try:
        import requests
        from bs4 import BeautifulSoup
        return requests, BeautifulSoup
    except Exception:
        return None, None

def _parse_date_any(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s: return None
    s = re.sub(r"(?i)\b(midday|evening|mid\s*day)\b", "", s).strip()
    for fmt in ("%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(s, fmt)
        except Exception: pass
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", s)
    if m:
        for fmt in ("%m/%d/%Y","%m/%d/%y"):
            try: return datetime.strptime(m.group(1), fmt)
            except Exception: pass
    try:
        dt = pd.to_datetime(s, errors="coerce", infer_datetime_format=True)
        if pd.notna(dt): return dt.to_pydatetime()
    except Exception:
        pass
    return None

def _parse_soup(soup) -> pd.DataFrame:
    recs: List[dict] = []
    for tr in soup.find_all("tr"):
        cols = [c.get_text(" ", strip=True) for c in tr.find_all(["td","th"])]
        if len(cols) < 2: continue
        dt = _parse_date_any(" ".join(cols[:2]))
        if not dt: continue
        tail = " ".join(cols[1:])
        nums = [int(x) for x in re.findall(r"\b\d\b", tail)]
        if len(nums) < 3:
            nums = [int(x) for x in re.findall(r"\d", tail)][:3]
        if len(nums) >= 3:
            recs.append({"draw_date": dt, "white1": nums[0], "white2": nums[1], "white3": nums[2]})
    if not recs:
        for node in soup.find_all(True):
            txt = node.get_text(" ", strip=True)
            if not txt or len(txt) > 160: continue
            dt = _parse_date_any(txt)
            if not dt: continue
            nums = [int(x) for x in re.findall(r"\b\d\b", txt)]
            if len(nums) < 3:
                nums = [int(x) for x in re.findall(r"\d", txt)][:3]
            if len(nums) >= 3:
                recs.append({"draw_date": dt, "white1": nums[0], "white2": nums[1], "white3": nums[2]})
    return _normalize_df(pd.DataFrame(recs))

def _fetch_url(url: str) -> pd.DataFrame:
    requests, BeautifulSoup = _safe_requests_bs4()
    if not requests: return pd.DataFrame()
    try:
        headers = {"User-Agent": "AstroLotto/1.0"}
        r = requests.get(url, headers=headers, timeout=20); r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        return _parse_soup(soup)
    except Exception:
        return pd.DataFrame()

def update_pick3(root: Path) -> UpdateResult:
    cache_path = root / "Data" / "cached_pick3_data.csv"
    current = _read_cache(cache_path); last_count = len(current)
    urls = [
        "https://www.lotteryusa.com/colorado/pick-3/",
        "https://www.lotteryusa.com/colorado/pick-3/archive/",
        "https://www.lotteryusa.com/colorado/pick-3/results/",
        "https://www.lotteryusa.com/colorado/pick-3/archive/?page=all",
    ]
    merged = current.copy()
    used = []
    for u in urls:
        df = _fetch_url(u)
        if not df.empty:
            merged = pd.concat([merged, df], ignore_index=True)
            used.append(u.split('/colorado/')[-1].strip('/'))
    if used:
        merged = _normalize_df(merged); _write_cache(cache_path, merged)
        return UpdateResult(draws_added=max(0, len(merged)-last_count), jackpot_text=None, source_used="+".join(used))
    return UpdateResult(draws_added=0, jackpot_text=None, source_used="none")
