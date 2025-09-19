from typing import List
from .state import PickSet

class EVAvoidPopularPatterns:
    def __init__(self, popularity_model):
        self.pm = popularity_model

    def score_pattern_popularity(self, pick: PickSet) -> float:
        try:
            return float(self.pm.estimate(pick.white, pick.special))
        except Exception:
            return 0.0

    def rank(self, picks: List[PickSet], jackpot: int) -> List[PickSet]:
        ranked = []
        for p in picks:
            pop = self.score_pattern_popularity(p)
            base = float(p.meta.get("score", 0.5))
            penalty_strength = 0.25 if jackpot and jackpot > 300_000_000 else 0.5
            ev_score = base - penalty_strength * pop
            p.meta["popularity"] = pop
            p.meta["ev_score"] = ev_score
            ranked.append((ev_score, p))
        ranked.sort(key=lambda t: t[0], reverse=True)
        return [p for _, p in ranked]

    def filter_top_decile(self, picks: List[PickSet]) -> List[PickSet]:
        if not picks:
            return picks
        pops = [p.meta.get("popularity", 0.0) for p in picks]
        if not pops:
            return picks
        idx = max(0, int(len(pops) * 0.9) - 1)
        thresh = sorted(pops)[idx]
        return [p for p in picks if p.meta.get("popularity", 0.0) <= thresh]
