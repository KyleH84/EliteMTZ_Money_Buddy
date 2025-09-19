from __future__ import annotations
from typing import Mapping, Any, List
from .base import AgentResult
from . import tech_agent, pattern_agent, volatility_agent

def list_agent_fns():
    return [tech_agent.compute, pattern_agent.compute, volatility_agent.compute]

def list_agent_names() -> List[str]:
    return [fn.__module__.split(".")[-1].replace("_agent","") for fn in list_agent_fns()]

def compute_all(row: Mapping[str, Any]) -> List[AgentResult]:
    out: List[AgentResult] = []
    for fn in list_agent_fns():
        try:
            out.append(fn(row))
        except Exception as e:
            out.append(AgentResult(name=fn.__module__, score=0.0, detail=f"error: {e}"))
    return out
