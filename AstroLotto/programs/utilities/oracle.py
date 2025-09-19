
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import hashlib, random

def _seed(game: str, draw_date: str) -> int:
    h = hashlib.sha256(f"{game}|{draw_date}".encode()).hexdigest()
    return int(h[:16], 16)

def _dedupe_and_sort(nums: List[int]) -> List[int]:
    # Keep unique, sorted ascending (ball games look cleaner this way)
    return sorted(dict.fromkeys(int(n) for n in nums))

def _score_pick(pick: Dict[str, Any]) -> float:
    # Simple heuristic: reward spread-out whites and mid-range specials
    w = pick.get("white", []) or []
    if not w:
        return 0.0
    span = (max(w) - min(w)) if len(w) > 1 else 0
    # Encourage some spread without excluding tight combos entirely
    return 0.6 * (span) + 0.4 * (len(set(w)))

def _clamp_ranges(game: str, pick: Dict[str, Any]) -> Dict[str, Any]:
    # Non-authoritative guardrails; we assume upstream model used real ranges.
    # These clamps only kick in if numbers drift due to bad caches or mis-schema.
    g = game.lower()
    whites = list(pick.get("white", []) or [])
    special = pick.get("special", None)

    def clamp_list(vals, lo, hi):
        return [min(max(int(v), lo), hi) for v in vals]

    if g == "powerball":
        whites = clamp_list(whites, 1, 69)
        special = None if special is None else min(max(int(special), 1), 26)
    elif g == "megamillions":
        whites = clamp_list(whites, 1, 70)
        special = None if special is None else min(max(int(special), 1), 25)
    elif g == "luckyforlife":
        whites = clamp_list(whites, 1, 48)
        special = None if special is None else min(max(int(special), 1), 18)
    elif g == "colorado":  # Colorado Lotto+
        whites = clamp_list(whites, 1, 40)  # practical guard (historically 1..40)
        special = None
    elif g == "cash5":
        whites = clamp_list(whites, 1, 32)  # CO Cash 5 is 1..32
        special = None
    elif g == "pick3":
        whites = clamp_list(whites, 0, 9)
        special = None

    # Sort and ensure unique for ball games (except pick3 which allows repeats)
    if g != "pick3":
        whites = _dedupe_and_sort(whites)

    pick["white"] = whites
    pick["special"] = special
    return pick

def _diversify(picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Ensure the top few picks aren't near-duplicates
    seen = set()
    out = []
    for p in picks:
        key = (tuple(p.get("white", [])), p.get("special"))
        if key in seen:
            # small nudge: rotate last two whites
            w = list(p.get("white", []))
            if len(w) >= 2:
                w[-1], w[-2] = w[-2], w[-1]
                key = (tuple(w), p.get("special"))
                p["white"] = w
        seen.add(key)
        out.append(p)
    return out

def reshape(game: str, draw_date: str, picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Deterministic re-ranker with guardrails & mild variety
    rnd = random.Random(_seed(game, draw_date))

    # 1) Clamp to plausible ranges per game
    base = [_clamp_ranges(game, dict(p)) for p in picks]

    # 2) Score and sort (deterministic tiebreak using seed)
    scored: List[Tuple[float, int, Dict[str, Any]]] = []
    for i, p in enumerate(base):
        s = _score_pick(p)
        scored.append((s, i, p))
    scored.sort(key=lambda t: (-t[0], t[1]))

    ordered = [p for _, _, p in scored]

    # 3) Mild shuffle of lower-ranked items to avoid monotony
    tail = ordered[2:]
    rnd.shuffle(tail)
    ordered = ordered[:2] + tail

    # 4) De-duplicate near clones
    ordered = _diversify(ordered)

    return ordered
