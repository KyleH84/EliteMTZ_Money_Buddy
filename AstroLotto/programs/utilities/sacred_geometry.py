import numpy as np
def sacred_weights(white_max, strength=0.05):
    w=np.ones(white_max,dtype=float); return w/w.sum()
