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

from __future__ import annotations
import argparse, sys, asyncio, json, pandas as pd
from .modules.agents.orchestrator import AgentOrchestrator
from .modules.db_admin import ensure_db_ready
from .modules.agents.calibration import run_agents_calibration
from .modules.agents.auto_tune import latest_weights

def _print(df):
    try:
        print(df.to_string(index=False))
    except Exception:
        print(df)

def cmd_agents_batch(args):
    ensure_db_ready()
    symbols = []
    if args.universe and args.universe.lower() == "top100":
        # try load from universe CSV; fallback
        import os, pandas as pd
        path = str(BB_DATA / 'us_universe.csv')
        if os.path.exists(path):
            u = pd.read_csv(path)
            if "Ticker" in u.columns:
                symbols = u["Ticker"].dropna().astype(str).head(100).tolist()
        if not symbols:
            symbols = ["AAPL","MSFT","SPY","NVDA","AMZN","META","GOOGL","TSLA","AMD","NFLX"]
    else:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    priors = {s:0.5 for s in symbols}
    orch = AgentOrchestrator({})
    df = asyncio.run(orch.run_batch(symbols, priors=priors))
    _print(df[["Ticker","AgentsScore","AgentsConf","AgentsLabel"]])

def cmd_agents_calibrate(args):
    ensure_db_ready()
    df = run_agents_calibration(lookback_days=args.lookback, horizon_days=args.horizon, target_pct=args.target)
    _print(df)

def cmd_show_weights(args):
    w = latest_weights()
    print(json.dumps(w or {}, indent=2))

def main():
    p = argparse.ArgumentParser(prog="BreakoutBuddy CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("agents-batch")
    b.add_argument("--symbols", default="AAPL,MSFT,SPY", help="Comma-separated tickers or use --universe top100")
    b.add_argument("--universe", default="", help="Set to 'top100' to use Data/us_universe.csv head")
    b.set_defaults(func=cmd_agents_batch)

    c = sub.add_parser("agents-calibrate")
    c.add_argument("--lookback", type=int, default=120)
    c.add_argument("--horizon", type=int, default=5)
    c.add_argument("--target", type=float, default=3.0)
    c.set_defaults(func=cmd_agents_calibrate)

    w = sub.add_parser("show-weights")
    w.set_defaults(func=cmd_show_weights)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
