
# train_update.py - v10.3.6
# Automates: backfill -> train AUTO ensemble for all games -> print summary
import argparse, os, json
from utilities.ensemble import train_auto
import historical_backfill as hb

GAMES = ["powerball","mega_millions","colorado_lottery","cash5","pick3","lucky_for_life"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5, help="Years of history to backfill/fetch")
    ap.add_argument("--ag-preset", default="best_quality", help="AutoGluon preset if installed")
    args = ap.parse_args()

    print(f"[1/2] Backfill last {args.years} years...")
    added = hb.backfill(years_back=args.years)
    print(f"Backfill added rows: {added}")

    print("[2/2] Training AUTO ensembles...")
    out = {}
    for g in GAMES:
        res = train_auto(g, ".", ag_preset=args.ag_preset)
        out[g] = res
        print(f"{g}: {res}")

    summary_path = os.path.join(".", "models", "auto_train_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote summary: {summary_path}")

if __name__ == "__main__":
    main()
