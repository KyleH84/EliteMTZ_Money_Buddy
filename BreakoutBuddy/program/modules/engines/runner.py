from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from pathlib import Path
import pandas as pd

def _data_dir() -> Path:
    d = Path(__file__).resolve().parents[1] / "modules" / "Data"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _fallback_universe(n: int = 50) -> list[str]:
    base = [
        "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","NFLX","AVGO","JPM","BAC","XOM",
        "CVX","UNH","HD","KO","PEP","DIS","V","MA","CSCO","ORCL","CRM","INTC","ADBE","QCOM","TXN",
        "PFE","MRK","LLY","T","VZ","WMT","COST","NKE","BA","CAT","GS","MS","BK","USB","WFC",
    ]
    return base[:max(1, min(n, len(base)))]

def quick_scan(limit: int = 500) -> int:
    data_dir = _data_dir()
    try:
        from modules import data as data_mod
        from modules.services import scoring as scoring
    except Exception as e:
        syms = _fallback_universe( min(50, max(10, limit//10)) )
        df = pd.DataFrame({"Ticker": syms, "P_up": 0.55, "RelSPY": 0.0, "RVOL": 1.1})
        df.to_csv(data_dir / "watchlist_snapshot_latest.csv", index=False)
        rank = scoring._ensure_rank_cols(df) if hasattr(scoring, "_ensure_rank_cols") else df
        (data_dir / "ranked_latest.csv").write_text(rank.to_csv(index=False), encoding="utf-8")
        return len(df)
    try:
        tickers = data_mod.list_universe(limit)
    except Exception:
        tickers = []
    try:
        snap = data_mod.pull_enriched_snapshot(tickers) if tickers else pd.DataFrame()
    except Exception:
        snap = pd.DataFrame()
    if snap is None or snap.empty:
        syms = _fallback_universe( min(50, max(10, limit//10)) )
        snap = pd.DataFrame({"Ticker": syms, "P_up": 0.55, "RelSPY": 0.0, "RVOL": 1.1})
    snap.to_csv(data_dir / "watchlist_snapshot_latest.csv", index=False)
    try:
        ranked = scoring.rank_now(snap)
        if not isinstance(ranked, pd.DataFrame):
            ranked = ranked[-3] if isinstance(ranked, tuple) and len(ranked) >= 3 else snap
    except Exception:
        ranked = snap
    (data_dir / "ranked_latest.csv").write_text(ranked.to_csv(index=False), encoding="utf-8")
    return int(len(snap))
