from .state import RunState

class SupervisorAgent:
    def choose_mode(self, state: RunState, z_alignment: float | None = None) -> str:
        jackpot = state.artifacts.etl.get("jackpot", 0)
        oracle  = state.artifacts.oracle
        mode = state.inputs.mode

        if mode != "auto":
            return mode

        vix = getattr(oracle, "vix_close", 18.0) if oracle else 18.0
        kp  = getattr(oracle, "kp_3h_max", 2.0) if oracle else 2.0
        z_a = z_alignment if z_alignment is not None else 0.0

        if jackpot and jackpot > 300_000_000 and (vix > 25 or kp >= 5):
            return "rainbow"
        if kp >= 6 or z_a > 1.5:
            return "oracle_forward"
        return "most_likely"
