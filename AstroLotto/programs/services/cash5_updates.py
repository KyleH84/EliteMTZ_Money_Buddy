from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
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
    for i in range(1,7):
        col = f"white{i}"
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ("mega","powerball","lucky","cashball","bonus"):
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

def fetch_primary(url: str) -> Tuple[pd.DataFrame, Optional[str], str]:
    requests, BeautifulSoup = _safe_requests_bs4()
    if not requests: return pd.DataFrame(), None, "no-requests"
    try:
        headers = {"User-Agent": "AstroLotto/1.0"}
        r = requests.get(url, headers=headers, timeout=15); r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        records = []
        for node in soup.find_all(True):
            txt = node.get_text(" ", strip=True)
            if not txt: continue
            mdate = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", txt)
            if not mdate: continue
            try: dt = datetime.strptime(mdate.group(1), "%m/%d/%Y")
            except Exception: continue
            nums = [int(x) for x in re.findall(r"\b\d{1,2}\b", txt)]
            if len(nums) >= 5:
                white = nums[:5]; bonus = nums[5] if len(nums)>5 else None
                rec = {"draw_date": dt}
                for i, val in enumerate(white, 1): rec[f"white{i}"] = val
                if bonus is not None: rec["bonus"] = bonus
                records.append(rec)
        jp = None
        jpn = soup.find(string=re.compile("Jackpot", re.I))
        if jpn: jp = " ".join(jpn.parent.get_text(" ", strip=True).split())
        return _normalize_df(pd.DataFrame(records)), jp, url
    except Exception:
        return pd.DataFrame(), None, "fetch-failed"

def _update_generic(root: Path, cache_name: str, url: str) -> UpdateResult:
    cache_path = root / "Data" / cache_name
    current = _read_cache(cache_path); last_count = len(current)
    df, jp, src = fetch_primary(url)
    if not df.empty:
        import pandas as pd
        merged = pd.concat([current, df], ignore_index=True)
        merged = _normalize_df(merged); _write_cache(cache_path, merged)
        return UpdateResult(draws_added=len(merged)-last_count, jackpot_text=jp, source_used=src)
    return UpdateResult(draws_added=0, jackpot_text=None, source_used="none")

def update_cash5(root: Path) -> UpdateResult:
    return _update_generic(root, 'cached_cash5_data.csv', 'https://www.lotteryusa.com/colorado/cash-5/')
