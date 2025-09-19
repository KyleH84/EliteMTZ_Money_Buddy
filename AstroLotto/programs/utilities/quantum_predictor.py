import numpy as np
def quantum_probability_map(white_probs, special_probs=None, n_universes=1024, decoherence=0.15,
    observer_favored_whites=None, observer_favored_specials=None, observer_bias=0.2, seed=None):
    rng = np.random.default_rng(seed or 0)
    def norm(p): p=np.asarray(p,dtype=float); p=np.clip(p,1e-12,None); return p/p.sum()
    w0 = norm(white_probs); ws=[rng.dirichlet(w0*len(w0)*50.0) for _ in range(max(8,int(n_universes)))]
    wq = norm(np.mean(ws,axis=0))
    sq=None
    if special_probs is not None:
        s0 = norm(special_probs); ss=[rng.dirichlet(s0*len(s0)*50.0) for _ in range(max(8,int(n_universes//4)))]
        sq = norm(np.mean(ss,axis=0))
    return wq, sq, {"universes":float(n_universes),"decoherence":float(decoherence)}
