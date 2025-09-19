from __future__ import annotations
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
