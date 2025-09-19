
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
        path = "Data/us_universe.csv"
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
