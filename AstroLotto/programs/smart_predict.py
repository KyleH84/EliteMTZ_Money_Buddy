from __future__ import annotations
from typing import Dict, List, Any
import pandas as pd
from .montecarlo import monte_carlo_picks, choose_special

def predict_sets(game: str, df: pd.DataFrame, model: Dict[str,Any]|None, n_sets: int = 5,
                 short_days: int = 30, alpha: float = 0.3, gap_strength: float = 0.2,
                 n_sims: int = 5000, chaos_pct: float = 0.05) -> List[Dict[str,Any]]:
    whites_list = monte_carlo_picks(game, df, n_sets=n_sets, n_sims=n_sims,
                                    short_days=short_days, alpha=alpha,
                                    gap_strength=gap_strength, chaos_pct=chaos_pct)
    out = []
    for w in whites_list:
        spec = choose_special(game, df, model) if game in ("powerball","megamillions","luckyforlife") else ""
        out.append({"white": w, "special": spec, "notes": "smart-ensemble"})
    return out
