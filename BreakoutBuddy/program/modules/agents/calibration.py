
from __future__ import annotations
from typing import List
import numpy as np
import pandas as pd
import duckdb
from datetime import datetime, timedelta
from .cache import _conn

from ..labels import compute_labels_for_symbol

def _bin_stats(scores: pd.Series, hits: pd.Series, bins: List[float]) -> pd.DataFrame:
    b = pd.cut(scores, bins=bins, include_lowest=True, right=True)
    g = hits.groupby(b)
    out = pd.DataFrame({
        "Count": g.size(),
        "HitRate": g.mean(),
    }).reset_index().rename(columns={"score":"Bin"})
    out["BinLow"] = out["Bin"].apply(lambda x: float(x.left) if hasattr(x, "left") else np.nan)
    out["BinHigh"] = out["Bin"].apply(lambda x: float(x.right) if hasattr(x, "right") else np.nan)
    return out[["BinLow","BinHigh","Count","HitRate"]]

def run_agents_calibration(lookback_days: int = 120, horizon_days: int = 5, target_pct: float = 3.0) -> pd.DataFrame:
    """Compute reliability bins for AgentsScore versus +target_pct% in horizon_days."""
    con = _conn()
    since = f"current_timestamp - INTERVAL '{int(lookback_days)}' DAY"
    df = con.execute(f"""
        SELECT Ticker, AsOf::DATE as AsOfDate, AgentsScore, PriorPUp
        FROM AgentCache
        WHERE AsOf > {since}
        ORDER BY AsOf DESC
    """).fetchdf()

    if df.empty:
        return pd.DataFrame()

    # For each (Ticker, AsOfDate) compute forward label using yfinance via labels util
    rows = []
    for sym, g in df.groupby("Ticker"):
        lab = compute_labels_for_symbol(sym, horizon=horizon_days, target_pct=target_pct)
        if lab is None or lab.empty:
            continue
        lab["Date"] = pd.to_datetime(lab["Date"]).dt.tz_localize(None)
        lab.set_index("Date", inplace=True)
        for _, r in g.iterrows():
            asof = pd.to_datetime(r["AsOfDate"])
            try:
                # align to the closest trading day <= AsOf
                if asof not in lab.index:
                    # shift to previous available date
                    prev = lab.index[lab.index <= asof]
                    if len(prev)==0:
                        continue
                    asof_use = prev.max()
                else:
                    asof_use = asof
                col = f"Hit_+{int(target_pct)}in{horizon_days}d"
                hit = int(lab.loc[asof_use, col])
                rows.append({"Ticker": sym, "AsOfDate": asof_use, "AgentsScore": float(r["AgentsScore"]), "Hit": hit})
            except Exception:
                continue

    if not rows:
        return pd.DataFrame()

    df2 = pd.DataFrame(rows)
    bins = [0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0]
    stats = _bin_stats(df2["AgentsScore"], df2["Hit"], bins=bins)
    stats["Metric"] = "AgentsScore"

    # Write to DB
    con.register("tmp_stats", stats)
    con.execute("DELETE FROM AgentCalib WHERE Metric = 'AgentsScore'")
    con.execute("INSERT INTO AgentCalib SELECT current_date, BinLow, BinHigh, Count, HitRate, Metric FROM tmp_stats")
    return stats
