from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


import json, datetime as dt
from pathlib import Path
from programs.utilities.planetary_alignment import planetary_features_for_date
from programs.utilities.historical_enrichment import enrich_all_cached
from programs.agent.langchain_lottery_agent import agent_response

def main():
    report = {"when": dt.datetime.now().isoformat()}
    report["planetary"] = planetary_features_for_date(dt.date.today())
    try:
        report["enrichment"] = enrich_all_cached(Path("Data"))
    except Exception as e:
        report["enrichment"] = {"error": str(e)}
    try:
        r = agent_response("most frequent numbers")
        report["agent_smoke"] = {"type": r.get("type")}
    except Exception as e:
        report["agent_smoke"] = {"error": str(e)}
    out = Path("Data/reports"); out.mkdir(parents=True, exist_ok=True)
    (out / "big_patch_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
