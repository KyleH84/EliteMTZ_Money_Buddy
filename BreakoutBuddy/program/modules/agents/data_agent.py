
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import asyncio
import pandas as pd
import yfinance as yf
from .base import BaseAgent, ProgressCB

class DataAgent(BaseAgent):
    name = "data"

    async def _run_impl(self, symbol: str, progress: ProgressCB = None):
        cfg = self.cfg or {}
        hp = cfg.get("hist_period","1y"); hi = cfg.get("hist_interval","1d")
        ip = cfg.get("intra_period","5d"); ii = cfg.get("intra_interval","30m")
        tk = yf.Ticker(symbol)
        hist = await asyncio.to_thread(tk.history, period=hp, interval=hi, auto_adjust=False)
        intra = await asyncio.to_thread(tk.history, period=ip, interval=ii, auto_adjust=False)
        try:
            info = await asyncio.to_thread(lambda: tk.fast_info.__dict__ if hasattr(tk, "fast_info") else {})
        except Exception:
            info = {}
        return {
            "hist": hist.reset_index() if isinstance(hist, pd.DataFrame) else pd.DataFrame(),
            "intra": intra.reset_index() if isinstance(intra, pd.DataFrame) else pd.DataFrame(),
            "info": info,
        }
