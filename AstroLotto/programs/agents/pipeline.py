
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import json
from pathlib import Path
from datetime import datetime
from .state import RunState
from .supervisor import SupervisorAgent
from .oracle_agent import OracleAgent
from .mc_agent import MonteCarloAgent
from .ev_agent import EVAvoidPopularPatterns
from .explainer_agent import ExplainerAgent
from .ops_agent import OpsHealthAgent

class AgentsPipeline:
    def __init__(self, *,
                 etl_fetch,
                 feature_engineer,
                 perball_model_score,
                 sampler_fn,
                 popularity_model,
                 oracle_fetchers,
                 freshness_checkers,
                 runs_dir: str = "Data/runs"):
        self.etl_fetch = etl_fetch
        self.feature_engineer = feature_engineer
        self.perball_model_score = perball_model_score
        self.mc = MonteCarloAgent(sampler_fn)
        self.ev = EVAvoidPopularPatterns(popularity_model)
        self.explainer = ExplainerAgent()
        self.ops = OpsHealthAgent(freshness_checkers)
        self.supervisor = SupervisorAgent()
        self.oracle = OracleAgent(oracle_fetchers)
        self.runs_dir = Path(runs_dir)

    def run(self, state: RunState) -> RunState:
        state.artifacts.etl = self.etl_fetch(state.inputs.game, state.inputs.draw_date)
        state.artifacts.oracle = self.oracle.run(state.inputs.draw_date)
        gain = (state.inputs.oracle_gain_override
                if state.inputs.oracle_gain_override is not None
                else self.oracle.propose_gain(state.artifacts.oracle))
        state.artifacts.telemetry["oracle_gain"] = gain

        state.inputs.mode = self.supervisor.choose_mode(state)

        state.artifacts.features = self.feature_engineer(
            state.inputs.game, state.artifacts.etl, state.artifacts.oracle, gain
        )

        state.artifacts.model_probs = self.perball_model_score(
            state.inputs.game, state.artifacts.features
        )

        state.artifacts.candidates = self.mc.sample(
            state.artifacts.model_probs, state.inputs.mode, seed=state.inputs.seed
        )

        jackpot = int(state.artifacts.etl.get("jackpot", 0) or 0)
        ranked = self.ev.rank(state.artifacts.candidates, jackpot=jackpot)
        filtered = self.ev.filter_top_decile(ranked) or ranked
        keep = 3 if state.inputs.mode in ("rainbow", "oracle_forward") else 1
        state.artifacts.picks = filtered[:keep]

        if state.artifacts.picks:
            evs = [p.meta.get("ev_score", 0.0) for p in state.artifacts.picks]
            state.artifacts.telemetry["ev_score"] = sum(evs)/len(evs)
        state.artifacts.telemetry["diversity_score"] = self._estimate_diversity(state.artifacts.picks)

        state.artifacts.explain = self.explainer.summarize(state)
        state.artifacts.health = self.ops.check()

        self._persist(state)
        return state

    def _persist(self, state: RunState):
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        outdir = self.runs_dir / state.inputs.game / ts
        try:
            outdir.mkdir(parents=True, exist_ok=True)
            (outdir / "inputs.json").write_text(json.dumps({
                "game": state.inputs.game,
                "mode": state.inputs.mode,
                "draw_date": state.inputs.draw_date.isoformat(),
                "oracle_gain": state.artifacts.telemetry.get("oracle_gain"),
                "seed": state.inputs.seed,
            }, indent=2))
            (outdir / "model_probs.json").write_text(json.dumps(state.artifacts.model_probs, indent=2))
            (outdir / "final_picks.json").write_text(json.dumps([{
                "white": p.white, "special": p.special, "meta": p.meta
            } for p in state.artifacts.picks], indent=2))
            (outdir / "health.json").write_text(json.dumps(state.artifacts.health, indent=2))
            (outdir / "telemetry.json").write_text(json.dumps(state.artifacts.telemetry, indent=2))
            if state.artifacts.explain:
                (outdir / "explain.txt").write_text(state.artifacts.explain)
        except Exception:
            pass

    @staticmethod
    def _estimate_diversity(picks):
        if not picks:
            return 0.0
        def dist(a, b):
            return len(set(a.white) ^ set(b.white)) + int(a.special != b.special)
        N = len(picks)
        if N == 1:
            return 1.0
        total = 0
        cnt = 0
        for i in range(N):
            for j in range(i+1, N):
                total += dist(picks[i], picks[j])
                cnt += 1
        return total / max(1, cnt)
