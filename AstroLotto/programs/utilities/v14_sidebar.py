"""
Sidebar utilities for AstroLotto — patched 2025-09-05T19:33:16
- Loads feature flags from extras/{features.json|v14_flags.json} if present
- Provides sensible defaults so UI doesn't hide controls when file is missing
"""
from __future__ import annotations
import json, logging, os
from pathlib import Path

try:
    import streamlit as st
except Exception:
    st = None

logger = logging.getLogger(__name__)

def _load_flags() -> dict:
    """Search common locations for feature flags and return a dict.
    Default to training enabled + admin tools visible if nothing found.
    """
    # Derive app root from this file: .../programs/utilities/v14_sidebar.py -> app root is 2 parents up
    base = Path(__file__).resolve().parents[2]
    candidates = [
        base / "extras" / "features.json",
        base / "extras" / "v14_flags.json",
        # fallback env overrides
        Path(os.environ.get("AL_FEATURES_PATH","")) if os.environ.get("AL_FEATURES_PATH") else None,
    ]
    data = {"enable_training": True, "show_admin_tools": True}
    for p in candidates:
        try:
            if p and p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                # Normalize a few possible key names
                if isinstance(payload, dict):
                    for k in ("enable_training","training_enabled","training"):
                        if k in payload: data["enable_training"] = bool(payload[k])
                    for k in ("show_admin_tools","admin_tools","admin"):
                        v = payload.get(k)
                        if isinstance(v, dict): v = v.get("tools", v.get("enabled", True))
                        if v is not None: data["show_admin_tools"] = bool(v)
                    # merge everything else transparently
                    for k,v in payload.items():
                        data.setdefault(k, v)
                break
        except Exception as e:
            logger.warning("Feature flag load failed from %s: %s", p, e)
    # Env var hard overrides
    if os.getenv("AL_ENABLE_TRAINING"):
        data["enable_training"] = os.getenv("AL_ENABLE_TRAINING","1") not in ("0","false","False")
    if os.getenv("AL_SHOW_ADMIN_TOOLS"):
        data["show_admin_tools"] = os.getenv("AL_SHOW_ADMIN_TOOLS","1") not in ("0","false","False")
    return data

def get_version() -> str:
    # Simple best-effort version reader
    try:
        base = Path(__file__).resolve().parents[2]
        vfile = base / "extras" / "version.txt"
        if vfile.exists():
            return vfile.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return "v14"

def render_version_badge(prefix: str = "AstroLotto"):
    if st is None:
        return
    version = get_version()
    st.sidebar.caption(f"{prefix}: {version}")

def render_experimental_sidebar() -> dict:
    """Return a dict of flags and render a minimal section."""
    flags = _load_flags()
    if st is None:
        return flags
    st.sidebar.header("Experimental Features")
    st.sidebar.toggle("Enable Training", value=bool(flags.get("enable_training", True)), key="al_feat_training")
    st.sidebar.toggle("Show Admin Tools", value=bool(flags.get("show_admin_tools", True)), key="al_feat_admin")
    # Persist toggles back to runtime flags only (no disk write here)
    flags["enable_training"] = bool(st.session_state.get("al_feat_training", flags.get("enable_training", True)))
    flags["show_admin_tools"] = bool(st.session_state.get("al_feat_admin", flags.get("show_admin_tools", True)))
    return flags
