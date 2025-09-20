from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# utilities/ticket_select.py - Patch 4 (v1.0)
# Greedy / diversified ticket selection using probability tables.
import numpy as np
from typing import Dict, List, Optional, Tuple
import random

GAME_RULES = {
    "powerball":   {"k_white": 5, "white_min": 1, "white_max": 69, "special_min": 1, "special_max": 26},
    "megamillions":{"k_white": 5, "white_min": 1, "white_max": 70, "special_min": 1, "special_max": 25},
    "colorado_lottery": {"k_white": 6, "white_min": 1, "white_max": 40, "special_min": None, "special_max": None},
    "cash5": {"k_white": 5, "white_min": 1, "white_max": 32, "special_min": None, "special_max": None},
    "pick3": {"k_white": 3, "white_min": 0, "white_max": 9, "special_min": None, "special_max": None},
    "lucky_for_life":{"k_white": 5, "white_min": 1, "white_max": 48, "special_min": 1, "special_max": 18},
}

def _norm_game(game: str) -> str:
    g = (game or "").lower().strip()
    if g.startswith("mega"): return "megamillions"
    if g.startswith("power"): return "powerball"
    if "colorado" in g and "lotto" in g: return "colorado_lottery"
    if g in ("cash5","cash 5"): return "cash5"
    if g in ("lfl","luckyforlife","lucky for life"): return "lucky_for_life"
    return g

def _weighted_sample_without_replacement(weights: np.ndarray, k: int, start_index: int = 1) -> List[int]:
    rng = np.random.default_rng()
    w = np.array(weights, dtype=float)
    w = np.maximum(w, 1e-12)
    keys = rng.random(w.shape) ** (1.0 / w)
    idx = np.argpartition(-keys, kth=min(k, len(keys)-1))[:k]
    idx = idx[np.argsort(-keys[idx])]
    return [int(i) + start_index for i in idx]

def select_tickets(
    prob_table: Dict[str, np.ndarray],
    game: str,
    n_tickets: int = 5,
    strategy: str = "balanced",
    seed: Optional[int] = None,
) -> List[Dict[str, List[int] or int]]:
    game = _norm_game(game)
    rules = GAME_RULES[game]
    k_white = rules["k_white"]
    wmin, wmax = rules["white_min"], rules["white_max"]
    smin, smax = rules["special_min"], rules["special_max"]

    if seed is not None:
        random.seed(seed); np.random.seed(seed)

    white_probs = prob_table.get("white")
    special_probs = prob_table.get("special")

    tickets = []
    used_counts = np.zeros_like(white_probs)
    penalty = 0.15 if strategy == "coverage" else (0.05 if strategy == "balanced" else 0.0)

    for t in range(n_tickets):
        adj = white_probs * np.exp(-penalty * used_counts)
        adj = adj / adj.sum()
        whites = _weighted_sample_without_replacement(adj, k_white, start_index=1)
        whites = sorted(whites)

        if special_probs is not None:
            sp = np.copy(special_probs)
            if tickets:
                last = tickets[-1]["special"]
                if last is not None and (smin is not None):
                    idx = last - smin
                    if 0 <= idx < sp.size: sp[idx] *= 0.9
            sp = sp / sp.sum()
            special = int(np.argmax(np.random.multinomial(1, sp))) + smin
        else:
            special = None

        tickets.append({"white": whites, "special": special})
        for n in whites:
            used_counts[n - 1] += 1

    return tickets

def enhance_from_raw_predictions(
    raw_picks: List[Dict[str, List[int] or int]],
    prob_table: Dict[str, np.ndarray],
    game: str,
    n_tickets: Optional[int] = None,
    strategy: str = "balanced",
    seed: Optional[int] = None,
) -> List[Dict[str, List[int] or int]]:
    game = _norm_game(game)
    keep = []
    rest = max(0, (n_tickets or len(raw_picks)) - 1)
    if raw_picks:
        keep.append(raw_picks[0])

    if rest > 0:
        add = select_tickets(prob_table, game, n_tickets=rest, strategy=strategy, seed=seed)
        keep.extend(add)
    return keep or raw_picks
