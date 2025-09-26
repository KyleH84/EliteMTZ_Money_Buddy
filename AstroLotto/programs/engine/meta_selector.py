from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# engine/meta_selector.py — Big Patch: consensus, intention-hash, shortlist, oracle chaos
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import datetime as dt
import hashlib

from utilities.probability import GAME_RULES
from utilities.quantum_predictor import quantum_probability_map
from utilities.archetypal_engine import archetypal_weights
from utilities.retrocausal_feedback import apply_retro_weights, RetroConfig
from utilities.per_ball_trainer import compute_per_position_probs
from utilities.per_ball_ml import predict_per_ball_ml, train_per_ball_ml
from utilities.sacred_geometry import sacred_weights
from utilities.performance_tracker import retro_memory_adjust
from utilities.qrng import qrng_seed

def _ensure_probs(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    x = np.clip(x, 1e-12, None)
    x = x / x.sum()
    return x

def _mix_uniform(p: np.ndarray, alpha: float) -> np.ndarray:
    if alpha <= 0: return _ensure_probs(p)
    u = np.ones_like(p, dtype=float) / len(p)
    return _ensure_probs((1.0-alpha)*p + alpha*u)

def _compose_white_surface(base_white: np.ndarray,
                           per_pos_simple: List[np.ndarray],
                           per_pos_ml: List[np.ndarray],
                           sacred: np.ndarray,
                           arche_white: np.ndarray,
                           weights: Tuple[float,float,float,float] = (0.55, 0.15, 0.20, 0.10)) -> np.ndarray:
    w = _ensure_probs(base_white)
    if per_pos_simple:
        w = _ensure_probs(weights[0]*w + weights[1]*_ensure_probs(np.mean(np.vstack(per_pos_simple), axis=0)))
    if per_pos_ml:
        w = _ensure_probs((1.0-weights[2])*w + weights[2]*_ensure_probs(np.mean(np.vstack(per_pos_ml), axis=0)))
    w = _ensure_probs((1.0-weights[3])*w + weights[3]*_ensure_probs(_ensure_probs(sacred) * _ensure_probs(arche_white)))
    return w

def _intention_hash_bias(w: np.ndarray, intention: Optional[str], strength: float = 0.01) -> np.ndarray:
    if not intention or strength <= 0: return w
    h = hashlib.sha256(intention.encode("utf-8")).hexdigest()
    idxs = [int(h[i:i+4],16)%len(w) for i in range(0,16,4)]
    w2 = w.copy()
    for idx in idxs:
        w2[idx] *= (1.0 + strength)
    return _ensure_probs(w2)

def _ensemble_consensus(w: np.ndarray, n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    posts = []
    for _ in range(max(1,int(n))):
        alpha = w * len(w) * 50.0
        posts.append(rng.dirichlet(alpha))
    m = _ensure_probs(np.mean(np.vstack(posts), axis=0))
    return m

def meta_compose(game: str, df, date: dt.date, user: Dict[str,Any], opts: Dict[str,Any]):
    rules = GAME_RULES[game if game in GAME_RULES else game.replace(" ","").lower()]
    white_max = int(rules["white_max"])
    special_max = int(rules.get("special_max") or 0) or None

    base = opts.get("base") or {}
    w = _ensure_probs(base.get("white"))
    s = _ensure_probs(base.get("special")) if base.get("special") is not None else None

    per_pos_simple = compute_per_position_probs(game, df)["white"] if opts.get("use_per_ball") else []
    per_pos_ml = opts.get("per_ball_ml") or []

    sacred = sacred_weights(white_max, strength=float(opts.get("sacred_strength", 0.05))) if opts.get("use_sacred") else np.ones(white_max)/white_max
    arche = archetypal_weights(game, white_max, special_max, date, user_name=user.get("name"), birthdate=user.get("birthdate")) if opts.get("use_archetype") else {"white": np.ones(white_max)/white_max, "special": (np.ones(special_max)/special_max if special_max else None), "tarot_card": ""}

    w = _compose_white_surface(w, per_pos_simple, per_pos_ml, sacred, arche["white"])
    if s is not None and arche["special"] is not None:
        s = _ensure_probs(s * arche["special"])

    chaos = float(opts.get("oracle_chaos", 0.0))
    w = _mix_uniform(w, alpha=min(0.5, chaos))
    if s is not None:
        s = _mix_uniform(s, alpha=min(0.5, chaos*0.7))

    decoherence = float(opts.get("decoherence", 0.15))
    decoherence_eff = float(np.clip(decoherence + 0.6*chaos, 0.0, 0.80))
    observer_bias = float(opts.get("observer_bias", 0.20)) * (1.0 + 2.0*chaos)

    w = _intention_hash_bias(w, intention=opts.get("intention_text"), strength=float(opts.get("intention_strength", 0.01)))

    if opts.get("use_quantum"):
        seed = None
        if opts.get("use_qrng"):
            try:
                seed = int(qrng_seed())
            except Exception:
                seed = None
        w, s, _ = quantum_probability_map(
            white_probs=w, special_probs=s,
            n_universes=int(opts.get("universes", 1024)),
            decoherence=decoherence_eff,
            observer_favored_whites=user.get("lucky_whites"),
            observer_favored_specials=user.get("lucky_specials"),
            observer_bias=observer_bias,
            seed=seed,
        )
    if int(opts.get("ensembles", 1)) > 1:
        seed = int(opts.get("seed", 0)) or 0
        w = _ensemble_consensus(w, int(opts.get("ensembles", 1)), seed)

    if opts.get("use_retro"):
        mem = retro_memory_adjust(default_memory=float(opts.get("retro_memory", 0.35)))
        w, s, _ = apply_retro_weights(game, w, s, cfg=RetroConfig(horizon_days=int(opts.get("retro_horizon",120)), memory=mem))

    score_mult = opts.get("oracle_score_mult") or {}
    if score_mult:
        w2 = w.copy()
        for k,v in score_mult.items():
            try:
                idx = int(k)-1
                if 0 <= idx < len(w2): w2[idx] *= float(v)
            except (ValueError, TypeError):
                continue
        w = _ensure_probs(w2)

    return w, s, arche.get("tarot_card","")

def improve_picks(picks: List[Dict[str,Any]], w: np.ndarray, s: Optional[np.ndarray], shortlist_k: int = 0) -> List[Dict[str,Any]]:
    out = []
    top = np.argsort(w)[::-1] + 1
    shortlist = set(top[:max(0, int(shortlist_k))]) if shortlist_k else set()
    for p in picks:
        ws = list(p.get("white", []))
        base = float(sum(w[i-1] for i in ws))
        best = (None, 0.0, None)
        for cand in top[:15]:
            if cand in ws: continue
            for i in range(len(ws)):
                trial = ws.copy(); trial[i] = int(cand)
                if len(set(trial)) != len(trial): continue
                sc = float(sum(w[j-1] for j in trial))
                if sc > base * 1.02 and sc > best[1]:
                    best = (i, sc, cand)
        note = p.get("notes","")
        if best[0] is not None:
            old = ws[best[0]]; ws[best[0]] = int(best[2])
            note = (note + (" | " if note else "") + f"meta swapped {old}→{best[2]}")
        if shortlist and any(x not in shortlist for x in ws):
            for i in range(len(ws)):
                if ws[i] in shortlist: continue
                for cand in top[:len(shortlist)]:
                    if cand in ws: continue
                    trial = ws.copy(); trial[i] = int(cand)
                    if len(set(trial)) != len(trial): continue
                    sc = float(sum(w[j-1] for j in trial))
                    if sc >= base * 0.99:
                        note = (note + (" | " if note else "") + f"shortlist pull {ws[i]}→{cand}")
                        ws = trial; base = sc
                        break
        conf = float(sum(w[i-1] for i in ws)) / float(max(1e-8, w.sum()))
        note = (note + (" | " if note else "") + f"conf≈{conf:.2f}")
        out.append({"white": ws, "special": p.get("special"), "notes": note})
    return out
