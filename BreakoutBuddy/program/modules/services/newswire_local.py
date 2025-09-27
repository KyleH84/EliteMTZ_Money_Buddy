from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Dict, Iterable
import io, re
import pandas as pd
import streamlit as st

EXPECTED_COLS = ["Date","Company","Ticker","Sign","Headline","Link","Source"]

def _coerce_datetime(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce", utc=True)
    except Exception:
        return pd.to_datetime([], utc=True)

def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    lower = {c.lower(): c for c in df.columns}
    ren = {}
    for want in EXPECTED_COLS:
        if want in df.columns: continue
        if want.lower() in lower:
            ren[lower[want.lower()]] = want
    if ren:
        df = df.rename(columns=ren)
    for c in EXPECTED_COLS:
        if c not in df.columns:
            df[c] = ""
    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df["Ticker"] = df["Ticker"].str.replace(r"[^A-Z0-9.\-]", "", regex=True)
    if "Date" in df.columns:
        df["Date"] = _coerce_datetime(df["Date"])
    df = df[EXPECTED_COLS].copy()
    df = df.sort_values("Date", ascending=False, kind="stable")
    return df

@st.cache_data(ttl=900, show_spinner=False)
def load_news_csv(*, csv_bytes: Optional[bytes] = None, csv_path: Optional[Path] = None) -> pd.DataFrame:
    df = pd.DataFrame(columns=EXPECTED_COLS)
    try:
        if csv_bytes is not None:
            df = pd.read_csv(io.BytesIO(csv_bytes))
        elif csv_path is not None and csv_path.exists():
            df = pd.read_csv(csv_path)
    except Exception:
        return pd.DataFrame(columns=EXPECTED_COLS)
    return _normalize_cols(df)

def save_news_csv(df: pd.DataFrame, *, csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _normalize_cols(df).to_csv(csv_path, index=False)

def append_rows(rows: Iterable[Dict[str, str]], *, csv_path: Path) -> pd.DataFrame:
    base = load_news_csv(csv_path=csv_path) if csv_path.exists() else pd.DataFrame(columns=EXPECTED_COLS)
    add = pd.DataFrame(list(rows), columns=EXPECTED_COLS)
    df = pd.concat([add, base], ignore_index=True)
    df = _normalize_cols(df)
    df = df.drop_duplicates(subset=["Ticker","Headline","Date"], keep="first")
    save_news_csv(df, csv_path=csv_path)
    return df

def filter_recent(df: pd.DataFrame, *, hours: int = 12) -> pd.DataFrame:
    if df.empty or "Date" not in df.columns:
        return df.iloc[0:0]
    cutoff = pd.Timestamp.utcnow() - pd.Timedelta(hours=hours)
    return df[df["Date"] >= cutoff].copy()

def list_unique_tickers(df: pd.DataFrame) -> List[str]:
    if df.empty or "Ticker" not in df.columns:
        return []
    tickers = [t for t in df["Ticker"].astype(str) if t]
    tickers = [re.sub(r"[^A-Z0-9.\-]", "", t.upper()) for t in tickers]
    return sorted(set(tickers))

def parse_ticker_text(raw: str) -> List[str]:
    if not raw:
        return []
    toks = re.split(r"[\s,;]+", raw.upper())
    out = []
    for t in toks:
        t = re.sub(r"[^A-Z0-9.\-]", "", t)
        if t:
            out.append(t)
    return sorted(set(out))