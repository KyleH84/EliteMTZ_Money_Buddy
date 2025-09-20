from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any

@dataclass
class AppContext:
    data_dir: Path
    db_path: Path
    conn: Any
    has_agents: bool = False
    agent_err: Optional[str] = None
