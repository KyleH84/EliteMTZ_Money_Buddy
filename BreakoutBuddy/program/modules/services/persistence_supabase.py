from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Optional, List

import pandas as pd
from supabase import create_client, Client
import streamlit as st

# ---------- Config ----------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Buckets you should create once in the Supabase dashboard:
BUCKET_SNAPSHOTS = os.getenv("SUPABASE_BUCKET_SNAPSHOTS", "snapshots")
BUCKET_TABLES = os.getenv("SUPABASE_BUCKET_TABLES", "tables")

# Tables you should create once:
#   watchlist (ticker text, ns text, primary key(ticker,ns))
#   app_kv (ns text, k text, v text, primary key(ns, k))

@dataclass
class SB:
    client: Client

def _client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_KEY.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Watchlist (Postgres table) ----------

@st.cache_data(ttl=900, show_spinner=False)
def get_watchlist(app: str = "BB") -> List[str]:
    c = _client()
    try:
        resp = c.table("watchlist").select("ticker").eq("ns", app).order("ticker").execute()
        rows = resp.data or []
        return [str(r["ticker"]).upper() for r in rows]
    except Exception:
        resp = c.table("watchlist").select("ticker").execute()
        rows = resp.data or []
        return [str(r["ticker"]).upper() for r in rows]

def set_watchlist(tickers: List[str], app: str = "BB") -> None:
    c = _client()
    uniq = sorted({str(t).upper().strip() for t in tickers if t})
    try:
        c.table("watchlist").delete().eq("ns", app).execute()
    except Exception:
        c.table("watchlist").delete().neq("ticker", "__NOOP__").execute()
    rows = [{"ticker": t, "ns": app} for t in uniq]
    try:
        c.table("watchlist").upsert(rows).execute()
    except Exception:
        rows = [{"ticker": t} for t in uniq]
        c.table("watchlist").upsert(rows).execute()

def add_watch(ticker: str, app: str = "BB") -> None:
    if not ticker:
        return
    c = _client()
    row = {"ticker": str(ticker).upper().strip(), "ns": app}
    try:
        c.table("watchlist").upsert(row).execute()
    except Exception:
        del row["ns"]
        c.table("watchlist").upsert(row).execute()

def remove_watch(ticker: str, app: str = "BB") -> None:
    if not ticker:
        return
    c = _client()
    t = str(ticker).upper().strip()
    try:
        c.table("watchlist").delete().eq("ticker", t).eq("ns", app).execute()
    except Exception:
        c.table("watchlist").delete().eq("ticker", t).execute()

# ---------- Key/Value (small settings) ----------

def set_kv(ns: str, key: str, value: str) -> None:
    c = _client()
    row = {"ns": ns, "k": key, "v": str(value)}
    c.table("app_kv").upsert(row).execute()

@st.cache_data(ttl=900, show_spinner=False)
def get_kv(ns: str, key: str, default: Optional[str] = None) -> Optional[str]:
    c = _client()
    resp = c.table("app_kv").select("v").eq("ns", ns).eq("k", key).single().execute()
    if resp.data and "v" in resp.data:
        return resp.data["v"]
    return default

# ---------- Snapshots / DataFrames in Storage (Parquet) ----------

def save_snapshot(df: pd.DataFrame, name: str = "latest", app: str = "BB") -> None:
    if df is None or df.empty:
        return
    c = _client()
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    path = f"{app}/{name}.parquet"
    c.storage.from_(BUCKET_SNAPSHOTS).upload(
        path, buf, file_options={"cache-control": "no-cache", "upsert": "true"}
    )

@st.cache_resource(show_spinner=False)
def load_snapshot(name: str = "latest", app: str = "BB") -> pd.DataFrame:
    c = _client()
    path = f"{app}/{name}.parquet"
    try:
        res = c.storage.from_(BUCKET_SNAPSHOTS).download(path)
        if not res:
            return pd.DataFrame()
        buf = io.BytesIO(res)
        return pd.read_parquet(buf)
    except Exception:
        return pd.DataFrame()

# ---------- Generic Tables (CSV replacements) ----------

def save_table(df: pd.DataFrame, table_name: str, app: str = "BB") -> None:
    if df is None or df.empty:
        df = pd.DataFrame()
    c = _client()
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    path = f"{app}/{table_name}.parquet"
    c.storage.from_(BUCKET_TABLES).upload(
        path, buf, file_options={"cache-control": "no-cache", "upsert": "true"}
    )

@st.cache_resource(show_spinner=False)
def load_table(table_name: str, app: str = "BB") -> pd.DataFrame:
    c = _client()
    path = f"{app}/{table_name}.parquet"
    try:
        res = c.storage.from_(BUCKET_TABLES).download(path)
        if not res:
            return pd.DataFrame()
        buf = io.BytesIO(res)
        return pd.read_parquet(buf)
    except Exception:
        return pd.DataFrame()