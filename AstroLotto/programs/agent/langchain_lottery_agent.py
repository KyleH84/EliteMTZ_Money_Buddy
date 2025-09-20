from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


from typing import Dict, Any
from .tools.frequency_tool import frequency_analysis
from .tools.pattern_tool import pattern_detection
from .tools.ml_tool import ml_predictor
from .tools.stats_tool import statistical_summary
from .tools.viz_tool import frequency_chart

def agent_response(prompt: str, df_or_path=None) -> Dict[str, Any]:
    p = (prompt or "").lower()
    if "chart" in p:
        fig = frequency_chart(df_or_path)
        return {"type":"plotly","figure": fig}
    if "frequen" in p or "hot" in p or "cold" in p:
        return {"type":"json","data": frequency_analysis(df_or_path)}
    if "pattern" in p or "even" in p or "odd" in p or "sum" in p:
        return {"type":"json","data": pattern_detection(df_or_path)}
    if "model" in p or "predict" in p:
        return {"type":"json","data": ml_predictor(df_or_path)}
    if "stat" in p or "summary" in p:
        return {"type":"json","data": statistical_summary(df_or_path)}
    return {"type":"text","text":"Try: 'most frequent numbers', 'pattern summary', 'build a model', or 'show frequency chart'."}
