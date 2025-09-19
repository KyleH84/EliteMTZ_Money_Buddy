
# v10.3.1 - CLI/Streamlit-friendly trainer (uses enhanced features)
import os
from utilities.features import build_features, GAME_MAP
from utilities.model import train_model, save_model
from utilities.eval import walk_forward

MODELS_DIR = "models"

def train_game(game_key: str, root_dir: str = "."):
    results = {}
    for target in (["white"] + (["special"] if GAME_MAP[game_key]["special"] else [])):
        X, y = build_features(game_key, root_dir, target)
        if X.empty or y.empty:
            results[target] = {"ok": False, "reason": "no_data"}
            continue
        metrics = walk_forward(X, y, train_min=min(400, max(100, int(0.6*len(X)))))
        model = train_model(X, y)
        out = os.path.join(root_dir, MODELS_DIR, f"{game_key}_{target}.pkl")
        save_model(model, out)
        results[target] = {"ok": True, "metrics": metrics, "model_path": out}
    return results

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True, choices=list(GAME_MAP.keys()))
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    res = train_game(args.game, args.root)
    for k, v in res.items():
        print(f"[{args.game}:{k}] -> {v}")
