from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import json, datetime as dt
from pathlib import Path
from typing import Dict, List, Tuple, Any
import pandas as pd

DATA_KEYS = {
    "powerball": ("cached_powerball_data.csv", {"white":5, "special":True}),
    "megamillions": ("cached_megamillions_data.csv", {"white":5, "special":True}),
    "cash5": ("cached_cash5_data.csv", {"white":5, "special":False}),
    "pick3": ("cached_pick3_data.csv", {"white":3, "special":False}),
    "luckyforlife": ("cached_luckyforlife_data.csv", {"white":5, "special":True}),
    "colorado": ("cached_colorado_lottery_data.csv", {"white":6, "special":False}),
}

RANGES = {
    "powerball": ((1,69,5),(1,26)),
    "megamillions": ((1,70,5),(1,25)),
    "cash5": ((1,32,5), None),
    "pick3": ((0,9,3), None),
    "luckyforlife": ((1,48,5), (1,18)),
    "colorado": ((1,40,6), None),
}

def _white_cols(df: pd.DataFrame) -> List[str]:
    cols = [c for c in df.columns if c.lower().startswith("white")]
    if cols: 
        return sorted(cols, key=lambda x: int("".join([d for d in x if d.isdigit()]) or "0"))
    fall = [f"n{i}" for i in range(1,7) if f"n{i}" in df.columns]
    return fall

def _special_col(df: pd.DataFrame, game:str) -> str|None:
    for c in df.columns:
        lc = c.lower()
        if game=="powerball" and lc=="powerball": return c
        if game=="megamillions" and lc in ("mega_ball","megaball","mega"): return c
        if game=="luckyforlife" and lc in ("lucky_ball","luckyball","lucky"): return c
        if lc in ("special","bonus"): return c
    return None

def check_cache(DATA: Path) -> Tuple[List[str], Dict[str, Any]]:
    issues: List[str] = []
    metrics: Dict[str, Any] = {}
    for game,(fname, spec) in DATA_KEYS.items():
        f = DATA/fname
        gkey = f"{game}.cache"
        if not f.exists():
            issues.append(f"[{game}] missing file: {fname}")
            continue
        try:
            df = pd.read_csv(f)
        except Exception as e:
            issues.append(f"[{game}] unreadable: {fname}: {e}")
            continue
        if df.empty:
            # Header-only cache is not treated as an issue; mark metrics and continue
            metrics[gkey] = {"rows": 0, "date_min": None, "date_max": None}
            continue
        dmin=dmax=None
        if "draw_date" in df.columns:
            try:
                d = pd.to_datetime(df["draw_date"], errors="coerce")
                dmin = str(d.min().date())
                dmax = str(d.max().date())
            except Exception:
                pass
        whites = _white_cols(df)
        needed = spec["white"]
        if len(whites) < needed:
            issues.append(f"[{game}] expected {needed} white columns; found {len(whites)} -> {whites}")
        wr = RANGES[game][0]
        if wr:
            lo,hi,k = wr
            bad = []
            for c in whites[:needed]:
                s = pd.to_numeric(df[c], errors="coerce").dropna().astype(int)
                bad.extend(s[(s<lo)|(s>hi)].head(3).tolist())
            if bad:
                issues.append(f"[{game}] out-of-range whites detected (sample): {bad[:5]} not in [{lo},{hi}]")
        if spec["special"]:
            sc = _special_col(df, game)
            if not sc:
                issues.append(f"[{game}] missing special column")
            else:
                lo,hi = RANGES[game][1]
                s = pd.to_numeric(df[sc], errors="coerce").dropna().astype(int)
                if ((s<lo)|(s>hi)).any():
                    issues.append(f"[{game}] out-of-range specials detected in {sc} (expected [{lo},{hi}])")
        metrics[gkey] = {"rows": len(df), "date_min": dmin, "date_max": dmax}
    return issues, metrics

def check_models(MODELS: Path, DATA: Path) -> Tuple[List[str], Dict[str, Any]]:
    issues: List[str] = []
    metrics: Dict[str, Any] = {}
    for game in DATA_KEYS.keys():
        m = MODELS/f"{game}_model.json"
        if not m.exists():
            metrics[f"{game}.model"] = {"exists": False}
            continue
        try:
            import json
            model = json.loads(m.read_text(encoding="utf-8"))
        except Exception as e:
            issues.append(f"[{game}] unreadable model JSON: {e}")
            continue
        if not (("scores" in model) or ("white_scores" in model)):
            issues.append(f"[{game}] model lacks white scores ('scores' or 'white_scores')")
        if "special_scores" in model and model["special_scores"]:
            lo_hi = RANGES[game][1]
            if lo_hi:
                lo,hi = lo_hi
                bad = [k for k in map(int, model["special_scores"].keys()) if k<lo or k>hi]
                if bad:
                    issues.append(f"[{game}] model special_scores out-of-range keys: {bad[:5]} (expected [{lo},{hi}])")
        metrics[f"{game}.model"] = {"exists": True, "has_white": ("scores" in model) or ("white_scores" in model), "has_special": bool(model.get("special_scores"))}
    return issues, metrics

def check_predictions(DATA: Path) -> Tuple[List[str], Dict[str, Any]]:
    issues: List[str] = []
    metrics: Dict[str, Any] = {}
    for game in DATA_KEYS.keys():
        f = DATA/f"{game}_predictions.csv"
        if not f.exists():
            metrics[f"{game}.pred"] = {"exists": False}
            continue
        try:
            df = pd.read_csv(f)
        except Exception as e:
            issues.append(f"[{game}] predictions unreadable: {e}")
            continue
        need_cols = {"draw_date","white_balls","special","notes"}
        missing = [c for c in need_cols if c not in df.columns]
        if missing:
            issues.append(f"[{game}] predictions missing columns: {missing}")
        metrics[f"{game}.pred"] = {"exists": True, "rows": len(df)}
    return issues, metrics

def run_all(ROOT: Path) -> Dict[str, Any]:
    DATA = ROOT/"Data"
    MODELS = DATA/"models"
    out: Dict[str, Any] = {"ok": True, "issues": [], "metrics": {}}
    i1, m1 = check_cache(DATA)
    i2, m2 = check_models(MODELS, DATA)
    i3, m3 = check_predictions(DATA)
    all_issues = i1+i2+i3
    out["ok"] = len(all_issues)==0
    out["issues"] = all_issues
    out["metrics"] = {**m1, **m2, **m3}
    lines = ["## Diagnostics Report", f"_Generated {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}._",
             "### Summary",
             f"- Status: **{'OK' if out['ok'] else 'ATTENTION NEEDED'}**",
             f"- Issues found: **{len(all_issues)}**"]
    if all_issues:
        lines.append("### Issues")
        for s in all_issues:
            lines.append(f"- {s}")
    lines.append("### Metrics")
    for k,v in out["metrics"].items():
        lines.append(f"- {k}: {v}")
    out["markdown"] = "\n".join(lines)
    return out
