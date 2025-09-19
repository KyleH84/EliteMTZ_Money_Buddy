from __future__ import annotations
from typing import List
import pandas as pd
from modules import explain as explain_mod

def friendly_lines(row: pd.Series) -> List[str]:
    """Turn explain.explain_row text into a short bullet list."""
    try:
        text = explain_mod.explain_row(row) or ""
    except Exception:
        text = ""
    # Split into bullets by sentence-like boundaries
    parts = [p.strip(" .;") for p in text.replace("\n"," ").split(".") if p and p.strip()]
    return parts if parts else ["Standard setup."]

def short_why(row: pd.Series) -> str:
    try:
        text = explain_mod.explain_row(row) or ""
        return text.strip()
    except Exception:
        return "Standard setup."
