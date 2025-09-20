from __future__ import annotations
import pandas as pd
from pathlib import Path

def _data_dir() -> Path:
    d = Path(__file__).resolve().parents[1] / "Data"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _ensure_rank_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Combined" not in df.columns:
        pu = pd.to_numeric(df.get("P_up", 0.5), errors="coerce").fillna(0.5)
        rel = pd.to_numeric(df.get("RelSPY", 0.0), errors="coerce").fillna(0.0)
        rv  = pd.to_numeric(df.get("RVOL", 1.0), errors="coerce").fillna(1.0)
        df["Combined"] = (pu * 70.0 + rel * 10.0 + (rv - 1.0) * 20.0).clip(0, 100)
    try:
        from modules.services import agents_service as AS
        df = AS.enrich_scores(df)
    except Exception:
        pass
    sort_col = "Combined_with_agents" if "Combined_with_agents" in df.columns else "Combined"
    return df.sort_values(by=[sort_col], ascending=False).reset_index(drop=True)

def _fallback_rows(n: int) -> pd.DataFrame:
    syms = [
        "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","NFLX","AVGO","JPM","BAC","XOM",
        "CVX","UNH","HD","KO","PEP","DIS","V","MA","CSCO","ORCL","CRM","INTC","ADBE","QCOM","TXN"
    ][: max(1, n)]
    return _ensure_rank_cols(pd.DataFrame({"Ticker": syms, "P_up": 0.55, "RelSPY": 0.0, "RVOL": 1.1}))

def _persist_ranked(df: pd.DataFrame) -> None:
    try:
        (_data_dir() / "ranked_latest.csv").write_text(df.to_csv(index=False), encoding="utf-8")
    except Exception:
        pass

def rank_now(arg) -> pd.DataFrame | tuple:
    if isinstance(arg, pd.DataFrame):
        df = _ensure_rank_cols(arg)
        _persist_ranked(df)
        return df
    try:
        settings = dict(arg)
    except Exception:
        settings = {}
    try:
        uni_n = int(settings.get("universe_size", 300))
        top_n = int(settings.get("top_n", 25))
    except Exception:
        uni_n, top_n = 300, 25
    try:
        from modules import data as data_mod
        from modules import regime as regime_mod
        tickers = data_mod.list_universe(uni_n)
        snap = data_mod.pull_enriched_snapshot(tickers)
        ranked = _ensure_rank_cols(snap)
        if top_n and 0 < top_n < len(ranked):
            ranked = ranked.head(top_n)
        try:
            regime = regime_mod.compute_regime()
        except Exception:
            regime = {}
        _persist_ranked(ranked)
        return snap, regime, ranked, None, None
    except Exception:
        ranked = _fallback_rows(top_n)
        _persist_ranked(ranked)
        return pd.DataFrame(), {}, ranked, None, None
