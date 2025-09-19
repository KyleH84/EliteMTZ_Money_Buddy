from .state import OracleSignals
from statistics import mean

class OracleAgent:
    def __init__(self, fetchers):
        self.fetchers = fetchers

    def run(self, date) -> OracleSignals:
        vals = {k: f(date) for k, f in self.fetchers.items()}
        return OracleSignals(**vals)

    def propose_gain(self, s: OracleSignals) -> float:
        def z(x, lo, hi):
            try:
                xv = float(x)
            except Exception:
                return 0.0
            if xv != xv:
                return 0.0
            mid = (lo + hi) / 2.0
            span = max(1e-6, (hi - lo) / 2.0)
            zval = (xv - mid) / span
            return max(-3.0, min(3.0, zval))

        z_kp   = z(s.kp_3h_max, 1.0, 6.0)
        z_vix  = z(s.vix_close, 12.0, 30.0)
        z_aln  = z(s.alignment_index, 0.5, 2.5)
        z_flr  = z(s.flare_mx_72h, 0.0, 8.0)
        z_mret = 0.6 if s.mercury_retro else 0.0
        z_avg  = mean([z_kp, z_vix, z_aln, z_flr, z_mret])

        gain = 1.0 + (z_avg + 3.0) * (1.5 / 6.0)
        return float(max(1.0, min(2.5, gain)))
