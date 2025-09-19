
from __future__ import annotations
import pandas as pd
from pathlib import Path
from modules.explain import explain_for_row

def augment_ranked_csv(csv_path: str | Path) -> pd.DataFrame:
    p = Path(csv_path)
    df = pd.read_csv(p)
    if "QuickWhy" in df.columns and "RiskBadge" in df.columns:
        return df
    exps = df.apply(lambda r: explain_for_row(r.to_dict()), axis=1)
    df["QuickWhy"] = [e.get("quick","") for e in exps]
    df["RiskBadge"] = [e.get("risk_badge","") for e in exps]
    df.to_csv(p, index=False)
    return df
