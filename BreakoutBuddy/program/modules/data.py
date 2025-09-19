from __future__ import annotations
import os
from pathlib import Path

# ---------- Strict per-app Data/Extras resolver (BreakoutBuddy) ----------
from pathlib import Path
import os, sys
BB_HERE     = Path(__file__).resolve()
BB_APP_ROOT = BB_HERE.parents[1]   # .../BreakoutBuddy

def _bb_cloud_roots():
    h = Path.home()
    return [
        h / "OneDrive",
        h / "OneDrive - Personal",
        h / "OneDrive - Wagstaff Law Firm",
        h / "Dropbox",
        h / "Google Drive",
        h / "Library" / "CloudStorage" / "OneDrive",
        h / "Library" / "CloudStorage" / "Dropbox",
        h / "Library" / "CloudStorage" / "GoogleDrive",
    ]

def _bb_first_existing(paths):
    for p in paths:
        try:
            p2 = Path(p).expanduser().resolve()
            if p2.exists():
                return p2
        except Exception:
            pass
    return None

def bb_resolve_dir(preferred_env_var: str, fallback_name: str):
    """
    Strict per-app order (NO repo-level fallback):
      1) Env var (abs or relative)
      2) BB_APP_ROOT/<name>
      3) CWD/<name>
      4) Cloud roots: <BreakoutBuddy>/<name>
      5) Create BB_APP_ROOT/<name>
    """
    envv = os.environ.get(preferred_env_var, "").strip()
    if envv:
        cand = (Path(envv) if os.path.isabs(envv) else (Path.cwd() / envv))
        if cand.exists():
            return cand.resolve()

    hit = _bb_first_existing([BB_APP_ROOT / fallback_name, Path.cwd() / fallback_name])
    if hit:
        return hit

    cands = []
    for root in _bb_cloud_roots():
        cands += [
            root / BB_APP_ROOT.name / fallback_name,
            root / "Projects" / BB_APP_ROOT.name / fallback_name,
        ]
    hit = _bb_first_existing(cands)
    if hit:
        return hit

    target = (BB_APP_ROOT / fallback_name).resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target

BB_DATA   = bb_resolve_dir("BREAKOUTBUDDY_DATA",   "Data")
BB_EXTRAS = bb_resolve_dir("BREAKOUTBUDDY_EXTRAS", "extras")

bb_extras_src = (BB_EXTRAS / "src")
if bb_extras_src.exists() and str(bb_extras_src) not in sys.path:
    sys.path.insert(0, str(bb_extras_src))
# ---------- end resolver ----------
import math
import pandas as pd
import numpy as np
import duckdb
import yfinance as yf
from modules.services.ohlcv_cache import get_history
import re

def sanitize_symbol(sym: str) -> str:
    s = str(sym).strip().upper()
    if s.startswith('$'):
        s = s[1:]
    s = re.sub(r"[^A-Z0-9._-]", "", s)
    return s


# ---------- Utilities & DB ----------

def ensure_dirs(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)

def open_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    # Keep tables light and compatible with earlier code
    conn.execute("""
        CREATE TABLE IF NOT EXISTS models (
            created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            algo TEXT,
            auc DOUBLE,
            train_start DATE,
            train_end DATE,
            features TEXT,
            train_size INTEGER
        )
    """)
    return conn

# ---------- Universe ----------

_DEFAULT_UNIVERSE = [
    # A compact, diversified list (expandable); used if remote lists fail
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","NFLX","AVGO","JPM","BAC","XOM",
    "CVX","PFE","MRK","UNH","HD","KO","PEP","NKE","DIS","V","MA","CSCO","ORCL","CRM","INTC",
    "AMAT","ADBE","QCOM","TXN","IBM","MU","SHOP","PLTR","UBER","ABNB","PYPL","SQ","BABA",
    "T","VZ","SPY","QQQ","IWM","LCID","RIVN","SOFI","F","GM"
]

def list_universe(n: int) -> list[str]:
    n = max(1, min(int(n), 500))
    # If user has a prebuilt symbol list cached, prefer it. Otherwise use defaults.
    try:
        # Pull S&P500-ish list via yfinance if available
        tbl = yf.Tickers("^GSPC ^NDX")
        # If that didn't explode, just return a trimmed default anyway (yfinance has no direct list)
        return _DEFAULT_UNIVERSE[:n] if n <= len(_DEFAULT_UNIVERSE) else _DEFAULT_UNIVERSE
    except Exception:
        return _DEFAULT_UNIVERSE[:n]

# ---------- Indicators ----------

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    s = series.astype(float).copy()
    delta = s.diff()
    gain = (delta.clip(lower=0)).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)

def _streak_series(close: pd.Series) -> pd.Series:
    # +1/+2/... for consecutive ups, -1/-2/... for consecutive downs, 0 for flat
    s = close.astype(float).copy()
    updown = np.sign(s.diff()).fillna(0.0)
    # manual loop for robustness (avoids pandas GroupBy ambiguity on edge cases)
    streak = np.zeros(len(updown), dtype=float)
    last = 0.0
    for i in range(len(updown)):
        cur = float(updown.iat[i])
        if cur == 0.0:
            last = 0.0
        elif (cur > 0 and last >= 0) or (cur < 0 and last <= 0):
            last = last + cur if last != 0 else cur
        else:
            last = cur
        streak[i] = last
    return pd.Series(streak, index=close.index)

def _percent_rank(series: pd.Series, window: int = 100) -> pd.Series:
    s = series.astype(float)
    def pr(x):
        if len(x) <= 1:
            return 50.0
        r = pd.Series(x).rank(pct=True).iloc[-1] * 100.0
        return float(r)
    return s.rolling(window).apply(pr, raw=False)

def _connors_rsi(close: pd.Series) -> pd.Series:
    rsi3 = _rsi(close, 3)
    streak = _streak_series(close)
    rsi_streak = _rsi(streak, 2)
    pct_change = close.pct_change(fill_method="pad")
    pr100 = _percent_rank(pct_change, 100)
    out = (rsi3 + rsi_streak + pr100) / 3.0
    return out

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def _squeeze_hint(df: pd.DataFrame) -> pd.Series:
    # Simple proxy: 20d std of returns vs 120d percentile
    r = df["Close"].astype(float).pct_change(fill_method="pad")
    w20 = r.rolling(20).std()
    w120 = r.rolling(120).std()
    z = (w20 - w120.rolling(120).mean()) / (w120.rolling(120).std() + 1e-9)
    return (z < -0.5).astype(int)

def _normalize_ohlcv(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    # Handle yfinance MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    # Ensure the standard columns exist
    keep = [c for c in ["Open","High","Low","Close","Adj Close","Volume"] if c in df.columns]
    df = df[keep]
    if "Adj Close" in df.columns and "Close" not in df.columns:
        df.rename(columns={"Adj Close":"Close"}, inplace=True)
    return df

# ---------- Snapshot enrichment ----------

def enrich_last_row(df: pd.DataFrame, spy_close: float) -> dict:
    """Compute indicators and return the latest row as a flat dict.
    Robust to tiny history (falls back gracefully).
    """
    d = _normalize_ohlcv(df)
    if d.empty or "Close" not in d.columns:
        return {}

    close = d["Close"].astype(float)
    open_ = d.get("Open", close).astype(float)
    high = d.get("High", close).astype(float)
    low = d.get("Low", close).astype(float)
    vol = d.get("Volume", pd.Series(index=close.index, data=np.nan))

    # Guard against <2 rows for prev_close
    if len(close) >= 2:
        prev_close = float(close.iloc[-2])
        change_pct = float((float(close.iloc[-1]) / prev_close - 1.0) * 100.0)
    else:
        prev_close = float(close.iloc[-1])
        change_pct = 0.0

    rsi2 = _rsi(close, 2)
    rsi4 = _rsi(close, 4)
    crsi = _connors_rsi(close)
    rvol = (vol.astype(float) / vol.astype(float).rolling(20).mean()).replace([np.inf,-np.inf], np.nan).fillna(1.0)
    atr = _atr(d).fillna(0.0)
    ma200 = close.rolling(200).mean()
    pct_from_200 = ((close / ma200) - 1.0) * 100.0
    squeeze = _squeeze_hint(d)

    out = {
        "Ticker": None,
        "Date": close.index[-1],
        "Open": float(open_.iloc[-1]),
        "High": float(high.iloc[-1]),
        "Low": float(low.iloc[-1]),
        "Close": float(close.iloc[-1]),
        "Volume": float(vol.iloc[-1]) if len(vol) else np.nan,
        "ChangePct": change_pct,
        "RSI2": float(rsi2.iloc[-1]),
        "RSI4": float(rsi4.iloc[-1]),
        "ConnorsRSI": float(crsi.iloc[-1]),
        "RelSPY": float((close.pct_change(fill_method="pad").rolling(5).mean().iloc[-1]) - (0.0 if spy_close is None else 0.0)),
        "RVOL": float(rvol.iloc[-1]) if len(vol) else 1.0,
        "ATR": float(atr.iloc[-1]),
        "PctFrom200d": float(pct_from_200.iloc[-1]) if not math.isnan(pct_from_200.iloc[-1]) else 0.0,
        "SqueezeHint": int(squeeze.iloc[-1]) if len(squeeze) else 0,
    }
    return out

def pull_enriched_snapshot(tickers: list[str]) -> pd.DataFrame:
    """Return a DataFrame with one enriched row per ticker.

    Columns include: Ticker, Open, High, Low, Close, Volume, ChangePct,
    RSI2, RSI4, ConnorsRSI, RelSPY, RVOL, ATR, PctFrom200d, SqueezeHint
    """
    if not tickers:
        return pd.DataFrame()

    spy_close = None
    try:
        spy = get_history("SPY", period="1y", interval="1d")
        if not spy.empty:
            spy_close = float(_normalize_ohlcv(spy)["Close"].iloc[-1])
    except Exception:
        spy_close = None

    rows = []
    for sym in tickers:
        try:
            hist = get_history(sanitize_symbol(sym), period="1y", interval="1d")
            if hist is None or hist.empty:
                continue
            d = _normalize_ohlcv(hist)
            row = enrich_last_row(d, spy_close)
            if not row:
                continue
            row["Ticker"] = sym
            rows.append(row)
        except Exception:
            # Skip bad symbols silently
            continue

    df = pd.DataFrame(rows)
    # Robust typing
    for c in ["Open","High","Low","Close","Volume","ChangePct","RSI2","RSI4","ConnorsRSI","RelSPY","RVOL","ATR","PctFrom200d","SqueezeHint"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df
