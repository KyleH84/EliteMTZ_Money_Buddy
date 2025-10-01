from __future__ import annotations

import numpy as np
from typing import Optional, Sequence, Tuple

def _norm(a):
    if a is None: return None
    x = np.asarray(a, dtype=float)
    s = x.sum()
    return x / s if s > 0 else np.ones_like(x)/len(x)

def quantum_probability_map(
    white_probs, special_probs=None, n_universes: int = 1024,
    decoherence: float = 0.1,
    observer_favored_whites: Optional[Sequence[int]] = None,
    observer_favored_specials: Optional[Sequence[int]] = None,
    observer_bias: float = 0.15,
    seed: Optional[int] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray], str]:
    rng = np.random.default_rng(seed)
    w = _norm(white_probs); s = _norm(special_probs)

    if w is not None:
        if decoherence:
            w = np.clip(w + rng.normal(0, decoherence/50.0, size=len(w)), 0, None); w = w / w.sum()
        if observer_favored_whites:
            w2 = w.copy()
            for v in observer_favored_whites:
                i = int(v)-1
                if 0 <= i < len(w2): w2[i] *= (1+observer_bias)
            w = w2 / w2.sum()
    if s is not None:
        if decoherence:
            s = np.clip(s + rng.normal(0, decoherence/50.0, size=len(s)), 0, None); s = s / s.sum()
        if observer_favored_specials:
            s2 = s.copy()
            for v in observer_favored_specials:
                i = int(v)-1
                if 0 <= i < len(s2): s2[i] *= (1+observer_bias)
            s = s2 / s.sum()

    tarot = ""
    return w, s, tarot

def qrng_seed() -> int:
    import time, os
    return int((time.time_ns() ^ os.getpid()) & 0x7FFFFFFF)
