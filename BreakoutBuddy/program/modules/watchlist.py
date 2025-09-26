# program/modules/watchlist.py
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
import pandas as pd  # type: ignore

# Optional DuckDB import; do NOT hard-require at import time
DUCK_OK = True
try:
    import duckdb  # type: ignore
except Exception:
    DUCK_OK = False
    duckdb = None  # type: ignore

# Resolve BreakoutBuddy root and Data
APP_ROOT = Path(__file__).resolve().parents[2]   # program/
BB_ROOT = APP_ROOT.parents[0]
DATA_DIR = Path(os.getenv("BREAKOUTBUDDY_DATA", BB_ROOT / "Data")).expanduser().resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Optional scoring helpers
try:
    from modules.services import scoring as scoring_mod  # type: ignore
except Exception:
    scoring_mod = None  # type: ignore


def _load_any_snapshot() -> Optional[pd.DataFrame]:
    """Pick a reasonable CSV from Data/ as a base snapshot for the watchlist."""
    names = [
        "explore_snapshot_latest.csv",
        "explore_snapshot.csv",
        "snapshot_latest.csv",
        "universe_snapshot_latest.csv",
        "ranked_latest.csv",
        "ranked.csv",
        "watchlist_snapshot_latest.csv",
    ]
    for nm in names:
        p = DATA_DIR / nm
        if p.exists():
            try:
                df = pd.read_csv(p)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    return df
            except Exception:
                pass

    # Fallback to newest CSV
    newest = None
    try:
        newest = max(
            (p for p in DATA_DIR.glob("*.csv") if p.is_file()),
            key=lambda x: x.stat().st_mtime,
            default=None,
        )
    except Exception:
        pass
    if newest:
        try:
            return pd.read_csv(newest)
        except Exception:
            return None
    return None


def _ensure_ticker_column(df: pd.DataFrame) -> pd.DataFrame:
    if "Ticker" in df.columns:
        return df
    for c in df.columns:
        if str(c).lower() in ("ticker", "symbol"):
            return df.rename(columns={c: "Ticker"})
    return df


def _fallback_rank(df: pd.DataFrame) -> pd.DataFrame:
    """Create minimal ranking columns so the UI has something to show."""
    out = df.copy()

    def col(name: str):
        for c in out.columns:
            if c.lower() == name.lower():
                return c
        return None

    if col("Combined") is None:
        try:
            import numpy as np  # type: ignore
            cp = pd.to_numeric(out[col("ChangePct")], errors="coerce")
            rv = pd.to_numeric(out[col("RVOL")], errors="coerce")
            z = (cp - cp.mean()) / (cp.std() or 1.0) + (rv - rv.mean()) / (rv.std() or 1.0)
            out["Combined"] = z.fillna(0.0).round(4)
        except Exception:
            out["Combined"] = 0.0

    if col("AgentBoost_exact") is None:
        out["AgentBoost_exact"] = 0.0
    if col("Combined_with_agents") is None:
        base = col("Combined")
        out["Combined_with_agents"] = out[base] if base else 0.0

    return out


def enriched_snapshot(tickers: List[str], enrich_features_fn=None) -> pd.DataFrame:
    """Return a filtered/enriched DataFrame for watchlist tickers.
    Uses CSVs under Data/ by default so we work even when DuckDB isn't installed.
    """
    tickers = sorted({str(t).strip().upper() for t in (tickers or []) if str(t).strip()})
    if not tickers:
        return pd.DataFrame()

    base = _load_any_snapshot()
    if base is None or base.empty:
        return pd.DataFrame({"Ticker": tickers})

    base = _ensure_ticker_column(base)
    if "Ticker" not in base.columns:
        return pd.DataFrame({"Ticker": tickers})

    sub = base[base["Ticker"].astype(str).isin(tickers)].copy()
    # Ensure all requested tickers appear, even if not present in snapshot
    _all_req = pd.DataFrame({'Ticker': [str(t).strip().upper() for t in tickers]})
    sub = _all_req.merge(sub, on='Ticker', how='left')


    # Optional enrichment hook
    if enrich_features_fn is not None:
        try:
            sub = enrich_features_fn(sub) or sub
        except Exception:
            pass

    # Ensure rank columns
    if scoring_mod is not None and hasattr(scoring_mod, "_ensure_rank_cols"):
        try:
            sub = scoring_mod._ensure_rank_cols(sub)  # type: ignore
        except Exception:
            sub = _fallback_rank(sub)
    # Guarantee indicator columns exist with safe defaults
    _defaults = {
        'RelSPY': 0.0,
        'P_up': 0.55,
        'ConnorsRSI': 50.0,
        'SqueezeHint': 0.0,
        'RVOL': 1.0,
        'RSI4': 50.0,
        'ChangePct': 0.0,
    }
    for _c, _d in _defaults.items():
        if _c not in sub.columns:
            sub[_c] = _d
        else:
            try:
                sub[_c] = pd.to_numeric(sub[_c], errors='coerce') if isinstance(_d, (int, float)) else sub[_c]
                sub[_c] = sub[_c].fillna(_d)
            except Exception:
                pass

    else:
        sub = _fallback_rank(sub)

    desired = [
        "Ticker","Open","High","Low","Close","Volume",
        "ChangePct","P_up","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint",
        "Combined","AgentBoost_exact","Combined_with_agents",
    ]
    order = [c for c in desired if c in sub.columns] + [c for c in sub.columns if c not in desired]
    return sub[order].reset_index(drop=True)
