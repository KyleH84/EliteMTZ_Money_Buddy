
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

"""
Modules package for BreakoutBuddy helpers.
This makes temporal_agent and meta_temporal_ensemble importable as modules.*.
"""

__all__ = ["temporal_agent", "meta_temporal_ensemble"]
