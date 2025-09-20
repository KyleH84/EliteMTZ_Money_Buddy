
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# scripts/test_harness.py
import datetime as dt
import numpy as np
import pandas as pd
from utilities.probability import compute_number_probs
from engine.meta_selector import meta_compose, improve_picks
def main():
    df = pd.DataFrame({
        "date": ["2025-08-01","2025-08-05","2025-08-08","2025-08-12"],
        "n1": [5, 8, 12, 14],
        "n2": [12, 16, 19, 22],
        "n3": [23, 24, 28, 31],
        "n4": [34, 35, 41, 46],
        "n5": [55, 59, 60, 61],
        "s1": [9, 14, 12, 18],
    })
    game = "powerball"
    base = compute_number_probs(df, game)
    w, s, tarot = meta_compose(
        game=game, df=df, date=dt.date.today(),
        user=dict(name="Test User", birthdate=dt.date(1990,1,1), lucky_whites=[7,11], lucky_specials=[9]),
        opts=dict(
            base=base,
            use_per_ball=True, per_ball_ml=[],
            use_sacred=True, use_archetype=True,
            use_quantum=True, universes=512, decoherence=0.15, observer_bias=0.20,
            use_qrng=False,
            use_retro=True, retro_horizon=120, retro_memory=0.35,
            oracle_score_mult={}, oracle_chaos=0.05,
            intention_text="test intention", intention_strength=0.01,
            ensembles=5, seed=13,
        )
    )
    picks = [{"white":[1,2,3,4,5],"special":7,"notes":""}]
    picks = improve_picks(picks, w, s, shortlist_k=10)
    print("w len:", len(w), "s len:", 0 if s is None else len(s), "tarot:", tarot)
    print("pick:", picks[0])
if __name__ == "__main__":
    main()
