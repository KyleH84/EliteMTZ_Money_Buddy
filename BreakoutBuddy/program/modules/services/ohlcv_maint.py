# program/modules/services/ohlcv_maint.py
from __future__ import annotations
import os, time, json
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path
import streamlit as st

try:
    import yfinance as yf  # type: ignore
except Exception:
    yf = None  # type: ignore

# Location: program/modules/services/ohlcv_maint.py
# parents: [0]=services, [1]=modules, [2]=program, [3]=<BreakoutBuddy root>
APP_ROOT = Path(__file__).resolve().parents[3]

# Allow Data folder override via env, else default to BB/Data
_env_data = os.getenv("BREAKOUTBUDDY_DATA", "")
if _env_data:
    DATA_DIR = Path(_env_data).expanduser().resolve()
else:
    DATA_DIR = (APP_ROOT / "Data").resolve()

CACHE_DIR = DATA_DIR / "cache" / "ohlcv"
PERSISTED_DIR = DATA_DIR / "persisted"
BACKUP_DIR = APP_ROOT / "Backups"

for d in (DATA_DIR, CACHE_DIR, PERSISTED_DIR, BACKUP_DIR):
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

@dataclass
class RebuildResult:
    fetched: int = 0
    errors: Dict[str, str] = None  # type: ignore

def clear_cache(dry_run: bool = False) -> None:
    for p in CACHE_DIR.glob("*.csv"):
        try:
            if not dry_run:
                p.unlink()
        except Exception:
            pass

def rebuild_ohlcv(tickers: List[str], period: str = "1y", interval: str = "1d", batch_size: int = 40, sleep_s: float = 0.75) -> RebuildResult:
    res = RebuildResult(fetched=0, errors={})
    if yf is None:
        res.errors["__global__"] = "yfinance not installed"
        return res

    uniq: List[str] = []
    seen = set()
    for t in tickers or []:
        sym = str(t).strip().upper()
        if sym and sym not in seen:
            uniq.append(sym); seen.add(sym)

    for i in range(0, len(uniq), max(1, batch_size)):
        batch = uniq[i:i+batch_size]
        for sym in batch:
            try:
                hist = yf.Ticker(sym).history(period=period, interval=interval)
                if hist is None or hist.empty:
                    res.errors[sym] = "empty"
                    continue
                out = hist.reset_index().rename(columns={"index": "Date"})
                (CACHE_DIR / f"{sym}_{period}_{interval}.csv").write_text(out.to_csv(index=False), encoding="utf-8")
                res.fetched += 1
            except Exception as e:
                res.errors[sym] = str(e)
            time.sleep(sleep_s)
    return res

# ---------- Admin UI API (backward-compatible) ----------

def admin_panel(st):
    """Entry used by modules.tabs.admin: renders maintenance UI inline, honoring Data override."""
    render_ui(st)

def render_ui(st):
    st.subheader("OHLCV Cache Maintenance")
    st.caption(f"Cache dir: {CACHE_DIR}")
    period = st.selectbox("Period", ["1y", "2y", "5y"], index=0)
    interval = st.selectbox("Interval", ["1d"], index=0)
    batch_size = st.slider("Batch size", 20, 200, 40, 10)
    sleep_s = st.slider("Sleep (seconds)", 0.25, 2.0, 0.75, 0.05)
    custom = st.text_area("Tickers (space or comma separated; leave blank for defaults)", "")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Clear cache (csv)"):
            clear_cache(dry_run=False)
            st.success("Cache cleared.")
    with c2:
        if st.button("Rebuild now"):
            tickers = [t for t in custom.replace(",", " ").split() if t.strip()] or \
                      ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","NFLX","AVGO"]
            if yf is None:
                st.error("yfinance is not installed. Add 'yfinance>=0.2.40' to extras/requirements.txt.")
                return
            clear_cache(dry_run=False)
            with st.status("Fetching OHLCV from yfinance...", expanded=True) as status:
                res = rebuild_ohlcv(tickers, period=period, interval=interval, batch_size=batch_size, sleep_s=sleep_s)
                status.update(label="Complete", state="complete")
            st.code(json.dumps(res.__dict__, indent=2), language="json")
            if res.errors:
                st.warning("Some symbols failed (invalid tickers or temporary throttling).")
            else:
                st.success(f"Rebuilt cache for {res.fetched} symbols.")