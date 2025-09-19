
from __future__ import annotations
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
