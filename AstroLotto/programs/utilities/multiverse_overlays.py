from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# programs/utilities/multiverse_overlays.py
import datetime as dt
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import numpy as np

from .probability import compute_number_probs, GAME_RULES
from .quantum_predictor import quantum_probability_map
from .archetypal_engine import archetypal_weights
from .retrocausal_feedback import apply_retro_weights, RetroConfig

def _ranges_for(game: str) -> Tuple[int, Optional[int]]:
    key = game if game in GAME_RULES else game.replace(" ", "").lower()
    rules = GAME_RULES[key]
    return int(rules["white_max"]), int(rules["special_max"] or 0) or None

def _compose_probs(game: str, root_dir: Path, date: dt.date, user: Optional[Dict[str,Any]], quantum: Dict[str,Any]):
    import pandas as pd
    data_dir = root_dir / "Data"
    cache_map = {
        "powerball": "cached_powerball_data.csv",
        "megamillions": "cached_megamillions_data.csv",
        "cash5": "cached_cash5_data.csv",
        "pick3": "cached_pick3_data.csv",
        "luckyforlife": "cached_luckyforlife_data.csv",
        "colorado": "cached_colorado_lottery_data.csv",
        "colorado_lottery": "cached_colorado_lottery_data.csv",
    }
    cache = data_dir / cache_map.get(game, "")
    import pandas as pd
    df = pd.read_csv(cache) if cache.exists() else pd.DataFrame()
    base = compute_number_probs(df, game)
    w = base["white"]; s = base.get("special")

    wmax, smax = _ranges_for(game)
    arche = archetypal_weights(game, wmax, smax, date, user_name=(user or {}).get("name"), birthdate=(user or {}).get("birthdate"))
    w = (w * arche["white"]); w = w / w.sum()
    if s is not None and arche["special"] is not None:
        s = (s * arche["special"]); s = s / s.sum()

    w, s, qdiag = quantum_probability_map(
        white_probs=w, special_probs=s,
        n_universes=int(quantum.get("universes", 1024)),
        decoherence=float(quantum.get("decoherence", 0.15)),
        observer_favored_whites=(user or {}).get("lucky_whites"),
        observer_favored_specials=(user or {}).get("lucky_specials"),
        observer_bias=float(quantum.get("observer_bias", 0.2)),
        seed=quantum.get("seed"),
    )

    w, s, rdiag = apply_retro_weights(
        game, w, s,
        cfg=RetroConfig(
            horizon_days=int(quantum.get("retro_horizon", 120)),
            memory=float(quantum.get("retro_memory", 0.35)),
            data_dir=(root_dir / "Data"),
        )
    )
    diag = {"quantum": qdiag, "archetype": {"tarot_card": arche.get("tarot_card","")}, "retro": rdiag}
    return w, s, diag

def _improve_one_pick(game: str, pick: Dict[str,Any], w: np.ndarray, s: Optional[np.ndarray]):
    whites = list(pick["white"])
    def score(ws):
        return float(sum(w[i-1] for i in ws))
    baseline = score(whites)
    top_candidates = np.argsort(w)[::-1][:10] + 1
    for cand in top_candidates:
        if cand in whites:
            continue
        for i in range(len(whites)):
            trial = whites.copy()
            trial[i] = int(cand)
            if len(set(trial)) != len(trial):
                continue
            if score(trial) > baseline * 1.02:
                whites = trial
                note = f"quantum/archetypal boost swapped {pick['white'][i]}→{cand}"
                return {"white": whites, "special": pick.get("special"), "notes": pick.get("notes","")}, note
    return pick, ""

def apply_overlays(game: str, draw_date: str, picks: List[Dict[str,Any]],
                   root_dir: Optional[str] = None,
                   settings: Optional[Dict[str,Any]] = None,
                   user: Optional[Dict[str,Any]] = None) -> List[Dict[str,Any]]:
    try:
        root = Path(root_dir or ".")
        date = dt.datetime.strptime(draw_date, "%Y-%m-%d").date() if isinstance(draw_date, str) else draw_date
        on = settings or {}
        if not (on.get("quantum") or on.get("archetype") or on.get("retro")):
            return picks

        w, s, diag = _compose_probs(game, root, date, user or {}, quantum=on.get("quantum_params", {}))

        out: List[Dict[str,Any]] = []
        for p in picks:
            newp, note = _improve_one_pick(game, p, w, s)
            conf = float(sum(w[i-1] for i in newp["white"])) / float(max(1e-8, w.sum()))
            msg = " | ".join(x for x in [newp.get("notes","").strip(), note.strip(),
                                         f"conf≈{conf:.2f}", f"tarot={diag.get('archetype',{}).get('tarot_card','')}"] if x)
            out.append({"white": newp["white"], "special": newp.get("special"), "notes": msg})
        return out
    except Exception:
        return picks
