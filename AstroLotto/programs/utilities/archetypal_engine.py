import numpy as np, datetime as dt
def archetypal_weights(game, white_max, special_max, date, user_name=None, birthdate=None):
    w = np.ones(white_max)/white_max
    s = np.ones(special_max)/special_max if special_max else None
    return {"white": w, "special": s, "tarot_card": ""}
