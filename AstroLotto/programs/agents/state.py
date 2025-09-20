
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

@dataclass
class PickSet:
    white: List[int]
    special: int
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OracleSignals:
    lunar_phase_frac: float
    kp_3h_max: float
    ap_daily: float
    f10_7: float
    flare_mx_72h: int
    alignment_index: float
    mercury_retro: bool
    vix_close: float

@dataclass
class RunInputs:
    game: str
    draw_date: datetime
    mode: str  # "most_likely" | "rainbow" | "oracle_forward" | "auto"
    seed: Optional[int] = None
    oracle_gain_override: Optional[float] = None

@dataclass
class RunArtifacts:
    etl: Dict[str, Any] = field(default_factory=dict)
    oracle: Optional[OracleSignals] = None
    features: Any = None
    model_probs: Dict[str, Any] = field(default_factory=dict)
    candidates: List[PickSet] = field(default_factory=list)
    picks: List[PickSet] = field(default_factory=list)
    explain: str = ""
    health: Dict[str, Any] = field(default_factory=dict)
    telemetry: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RunState:
    inputs: RunInputs
    artifacts: RunArtifacts = field(default_factory=RunArtifacts)
