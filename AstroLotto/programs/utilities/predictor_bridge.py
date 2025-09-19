# Program/utilities/predictor_bridge.py
from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict
import pandas as pd, numpy as np
from .feature_builder import build_inference_frame
from .model_loader import load_predictor
from .features_numeric import rules_for_game
from .chaos_signals import chaos_level_for_date
from .probability import compute_number_probs

def _blend(a: np.ndarray, b: np.ndarray, w: float) -> np.ndarray:
    w = float(max(0.0, min(1.0, w)))
    x = w*a + (1.0-w)*b
    s = x.sum()
    return x/s if s>0 else np.full_like(a, 1.0/len(a))

def _fallback_freq_table(game: str) -> Optional[Dict[str,np.ndarray]]:
    # use cached CSVs to compute baseline frequency table
    from os import environ as env
    data_dir = Path(env.get("ASTRO_DATA_DIR","Data"))
    import pandas as pd
    for p in data_dir.glob("cached_*_data.csv"):
        if game.replace('_','') in p.name.lower() or "mega" in (game+':'+p.name.lower()) or "power" in (game+':'+p.name.lower()):
            try:
                df=pd.read_csv(p)
                return compute_number_probs(df, game)
            except Exception:
                continue
    return None

def get_prob_table_or_none(game: str, draw_date) -> Optional[Dict[str,np.ndarray]]:
    k,wmin,wmax,smin,smax = rules_for_game(game)
    inf = build_inference_frame(game, draw_date, Path("Extras"), Path("Program"))
    if inf is None or inf.empty: 
        return _fallback_freq_table(game)

    white_pred = load_predictor(game, "white")
    special_pred = load_predictor(game, "special") if smin is not None else None
    if white_pred is None and (smin is None or special_pred is None):
        return _fallback_freq_table(game)

    # Split rows
    whites = inf[inf["head"]=="white"].copy()
    specials = inf[inf["head"]=="special"].copy() if smin is not None else None

    # Predict probabilities for class 1 (drawn)
    def proba_for(pred, df):
        try:
            prob = pred.predict_proba(df).get(1)
        except Exception:
            # some learners return numpy array
            p = pred.predict_proba(df)
            prob = p[:,1] if hasattr(p, "shape") and p.shape[1]>=2 else p
        return np.asarray(prob, dtype=float)

    white_probs = None
    if white_pred is not None and not whites.empty:
        wp = proba_for(white_pred, whites)
        white_probs = np.zeros(wmax - wmin + 1, dtype=float)
        for i, n in enumerate(whites["candidate_number"].values):
            white_probs[int(n)-wmin] = float(wp[i])
        s = white_probs.sum()
        white_probs = white_probs/s if s>0 else np.full_like(white_probs, 1.0/len(white_probs))

    special_probs = None
    if smin is not None and special_pred is not None and specials is not None and not specials.empty:
        sp = proba_for(special_pred, specials)
        special_probs = np.zeros(smax - smin + 1, dtype=float)
        for i, n in enumerate(specials["candidate_number"].values):
            special_probs[int(n)-smin] = float(sp[i])
        s = special_probs.sum()
        special_probs = special_probs/s if s>0 else np.full_like(special_probs, 1.0/len(special_probs))

    # Blend with baseline frequency table
    base = _fallback_freq_table(game)
    if base is None:
        base = {"white": np.full(wmax - wmin + 1, 1.0/(wmax-wmin+1)),
                "special": (None if smin is None else np.full(smax - smin + 1, 1.0/(smax-smin+1)))}
    blend_w = float(Path(".").stat().st_mtime % 100)  # deterministic-ish seed
    try:
        import os, time
        blend = float(os.environ.get("ASTRO_MODEL_BLEND","0.7"))
    except Exception:
        blend = 0.7

    chaos = chaos_level_for_date(pd.to_datetime(draw_date).date())
    # use chaos to slightly flatten the distribution (more exploration)
    def temper(p, temp):
        if p is None: return None
        q = np.power(p, 1.0/(1e-6+temp))
        q = q/q.sum()
        return q

    white_final = _blend(white_probs if white_probs is not None else base["white"], base["white"], blend)
    white_final = temper(white_final, 1.0 + 0.25*chaos)

    special_final = None
    if smin is not None:
        sp_base = base.get("special")
        sp_model = special_probs if special_probs is not None else sp_base
        if sp_base is None: sp_base = sp_model
        if sp_base is None: sp_base = np.full(smax - smin + 1, 1.0/(smax-smin+1))
        special_final = _blend(sp_model, sp_base, blend) if sp_model is not None else sp_base
        special_final = temper(special_final, 1.0 + 0.25*chaos)

    return {"white": white_final, "special": special_final}
