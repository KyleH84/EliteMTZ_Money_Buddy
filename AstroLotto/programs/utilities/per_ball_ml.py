
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

def train_per_ball_ml(game, df, neg_per_pos=4): return {"models":[], "white_max":0,"white_count":0}
def predict_per_ball_ml(df, model_pack): return []
