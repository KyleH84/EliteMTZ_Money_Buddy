
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


# Lightweight agents package so the Agents tab can import cleanly.
# Real logic lives in modules.services.agents_service.
from .base import safe_float  # re-export for convenience

HAS_AGENTS = True  # signal to UI tabs that agents exist
