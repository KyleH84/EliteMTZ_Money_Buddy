
# Lightweight agents package so the Agents tab can import cleanly.
# Real logic lives in modules.services.agents_service.
from .base import safe_float  # re-export for convenience

HAS_AGENTS = True  # signal to UI tabs that agents exist
