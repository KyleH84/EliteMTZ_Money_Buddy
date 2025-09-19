
from __future__ import annotations
from pathlib import Path
import pandas as pd
from .labels import compute_labels_for_symbol

def _engine_cols(): 
    return ["BreakoutOK","CrosserOK","BoxOK","RetailFadeOK"]

def compute_p_at_20(data_dir: Path, horizon_days: int = 5, target_pct: float = 3.0, max_days: int = 15) -> pd.DataFrame:
    """
    Reads Data/predictions/*.csv and computes P@20 per engine for logs older than horizon_days.
    This uses yfinance to compute labels on the fly.
    """
    pred_dir = data_dir / "predictions"
    rows = []
    if not pred_dir.exists():
        return pd.DataFrame(columns=["Engine","Days","Top20_Count","Hits","P@20"])
    csvs = sorted(pred_dir.glob("*.csv"))
    import datetime as dt
    cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=horizon_days)
    considered = [p for p in csvs if pd.Timestamp(p.stem) <= cutoff]
    # limit to recent max_days to keep it fast
    considered = considered[-max_days:]
    for f in considered:
        try:
            df = pd.read_csv(f)
        except Exception:
            continue
        asof = pd.to_datetime(df.get("AsOfDate").iloc[0]) if "AsOfDate" in df.columns else pd.Timestamp(f.stem)
        for eng_col, eng_name in zip(_engine_cols(), ["Breakout","Crosser","Box","RetailFade"]):
            if eng_col not in df.columns:
                continue
            sub = df[df[eng_col]==1].copy()
            if sub.empty: 
                continue
            # rank by EngineScore if available, else FinalScore or P_up
            if "EngineScore" in sub.columns:
                sub = sub.sort_values("EngineScore", ascending=False)
            elif "FinalScore" in sub.columns:
                sub = sub.sort_values("FinalScore", ascending=False)
            elif "P_up" in sub.columns:
                sub = sub.sort_values("P_up", ascending=False)
            top = sub.head(20)
            hits = 0; total = 0
            for _, r in top.iterrows():
                sym = str(r.get("Ticker","")).upper()
                if not sym: 
                    continue
                lab = compute_labels_for_symbol(sym, horizon=horizon_days, target_pct=target_pct)
                if lab is None or lab.empty:
                    continue
                # find row at or just before asof
                lab["Date"] = pd.to_datetime(lab["Date"])
                prev = lab[lab["Date"]<=asof]
                if prev.empty:
                    continue
                row = prev.iloc[-1]
                hit = int(row[f"Hit_+{int(target_pct)}in{horizon_days}d"])
                hits += hit; total += 1
            if total>0:
                rows.append({"Engine": eng_name, "Date": asof.date(), "Top20_Count": total, "Hits": hits})
    if not rows:
        return pd.DataFrame(columns=["Engine","Days","Top20_Count","Hits","P@20"])
    agg = pd.DataFrame(rows).groupby("Engine").agg(Days=("Date","nunique"), Top20_Count=("Top20_Count","sum"), Hits=("Hits","sum")).reset_index()
    agg["P@20"] = (agg["Hits"] / agg["Top20_Count"]).round(3)
    return agg
