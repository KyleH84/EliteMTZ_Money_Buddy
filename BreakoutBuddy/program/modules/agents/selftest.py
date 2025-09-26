from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import asyncio, pandas as pd
from .agents.orchestrator import AgentOrchestrator

DEFAULTS = ["AAPL","MSFT","SPY"]

async def _run(symbols):
    orch = AgentOrchestrator({})
    res = await orch.run_batch(symbols, priors={s:0.5 for s in symbols})
    return res

def run_selftest(symbols=None) -> dict:
    symbols = symbols or DEFAULTS
    try:
        df = asyncio.run(_run(symbols))
        ok = isinstance(df, pd.DataFrame) and not df.empty and set(["Ticker","AgentsScore","AgentsConf"]).issubset(df.columns)
        return {"ok": bool(ok), "rows": int(len(df)), "symbols": symbols}
    except Exception as e:
        return {"ok": False, "error": str(e), "symbols": symbols}
