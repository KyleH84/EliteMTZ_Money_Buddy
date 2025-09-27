# utilities/data_registry.py
# Locates the most recent snapshot/export under Data/, reads it, and exposes a shared refresh epoch.
import os, glob, time
import pandas as pd
import streamlit as st
from utilities.caching import cache_data

SNAP_PATTERNS = [
    "**/*candidates*.parquet", "**/*candidates*.feather", "**/*candidates*.csv",
    "**/*snapshot*.parquet",   "**/*snapshot*.feather",   "**/*snapshot*.csv",
]

def _find_latest_file(root='Data'):
    best_path, best_mtime = None, -1
    for pat in SNAP_PATTERNS:
        for p in glob.glob(os.path.join(root, pat), recursive=True):
            try:
                mt = os.path.getmtime(p)
                if mt > best_mtime:
                    best_mtime, best_path = mt, p
            except Exception:
                pass
    return best_path, best_mtime

def _read_any(path: str) -> pd.DataFrame:
    if path.endswith(".parquet"): return pd.read_parquet(path)
    if path.endswith(".feather"): return pd.read_feather(path)
    if path.endswith(".csv"):     return pd.read_csv(path)
    raise ValueError(f"Unsupported snapshot type: {path}")

@cache_data(ttl=120)
def load_active_snapshot(epoch: int) -> tuple[pd.DataFrame, str]:
    path, mtime = _find_latest_file('Data')
    if not path:
        raise FileNotFoundError("No snapshot found under Data/. Expected *candidates* or *snapshot* files.")
    df = _read_any(path)
    return df, path

def bump_refresh_epoch():
    st.session_state['snapshot_epoch'] = int(time.time())

def get_refresh_epoch() -> int:
    return st.session_state.get('snapshot_epoch', 0)