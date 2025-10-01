from __future__ import annotations
try:
    from ..utilities.cloud_paths import *  # re-export for modules.* import paths
except Exception:
    # fallback absolute import from program.utilities
    from BreakoutBuddy.program.utilities.cloud_paths import *
