
from __future__ import annotations
import os
try:
    import streamlit as st  # type: ignore
    _SECRETS = getattr(st, "secrets", {})
except Exception:
    _SECRETS = {}

def get_secret(name: str, default: str | None = None) -> str | None:
    # Prefer Streamlit secrets (Cloud/local), else environment
    if isinstance(_SECRETS, dict) and name in _SECRETS:
        return _SECRETS.get(name, default)
    if hasattr(_SECRETS, "get"):
        v = _SECRETS.get(name)
        if v is not None:
            return v
    return os.getenv(name, default)

def require_secret(name: str) -> str:
    v = get_secret(name)
    if not v:
        raise RuntimeError(f"Missing secret: {name} (set in .streamlit/secrets.toml or Cloud Secrets)")
    return v
