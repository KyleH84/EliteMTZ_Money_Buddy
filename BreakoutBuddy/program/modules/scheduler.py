
from __future__ import annotations
from datetime import datetime
import pandas as pd

def nightly_agents_calibration():
    from .agents.orchestrator import AgentOrchestrator
    orch = AgentOrchestrator({})
    stats = orch.run_calibration_now()
    return stats

def nightly_auto_tune():
    from .agents.orchestrator import AgentOrchestrator
    orch = AgentOrchestrator({})
    weights = orch.apply_auto_tune()
    return weights
