from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


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
