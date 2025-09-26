# sitecustomize.py
"""
BreakoutBuddy hardening (auto-loaded):

1) Force working directory to THIS folder (place this file in ...\BreakoutBuddy\).
2) Restore Streamlit API: experimental_rerun -> rerun.
3) Allow function args in @st.cache_data (hashing fix).
4) Accept width="stretch" in st.dataframe.
5) **STRICT PATH CLAMP**: Any attempt to create/write folders/files named
   'Data' or 'Backups' outside the project root is transparently redirected
   into the project root. This prevents accidental writes to parent folders
   when some module uses brittle Path.parents[...] math.
"""

from __future__ import annotations
import os
import builtins
import shutil
from pathlib import Path

# ------------------------ Detect and pin project root ------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
try:
    os.chdir(str(PROJECT_ROOT))
except Exception:
    pass
os.environ["BREAKOUTBUDDY_ROOT"] = str(PROJECT_ROOT)


# ------------------------ Streamlit shims ------------------------
def _patch_streamlit_rerun(st):
    try:
        if hasattr(st, "rerun") and not hasattr(st, "experimental_rerun"):
            setattr(st, "experimental_rerun", st.rerun)
    except Exception:
        pass

def _patch_streamlit_cache_hashing():
    try:
        from streamlit.runtime.caching import hashing  # type: ignore
    except Exception:
        try:
            from streamlit import hashing  # type: ignore
        except Exception:
            return
    try:
        def _hash_function_obj(obj):
            mod = getattr(obj, "__module__", None) or "builtins"
            name = getattr(obj, "__name__", None)
            if name:
                key = f"{mod}.{name}"
            else:
                key = f"{mod}.<lambda>@{hex(id(obj))}"
            return key.encode("utf-8")
        hashing.update_hash_funcs({type(lambda: None): _hash_function_obj})
    except Exception:
        pass

def _patch_streamlit_dataframe(st):
    try:
        orig_df = st.dataframe
        def df_wrapper(*args, **kwargs):
            w = kwargs.get("width", None)
            if isinstance(w, str) and w.strip().lower() == "stretch":
                kwargs.pop("width", None)
                kwargs["use_container_width"] = True
            return orig_df(*args, **kwargs)
        st.dataframe = df_wrapper  # type: ignore
    except Exception:
        pass


# ------------------------ Strict path clamp ------------------------
CLAMP_NAMES = {"data", "backups"}

def _normalize_target_path(p) -> Path:
    """Return a path guaranteed to be inside PROJECT_ROOT.
    If the basename is 'Data'/'Backups' and the path is outside root,
    redirect to PROJECT_ROOT/<basename>.
    """
    try:
        path = Path(p)
    except Exception:
        return PROJECT_ROOT  # degenerate fallback

    # If relative, anchor at project root
    if not path.is_absolute():
        return (PROJECT_ROOT / path).resolve()

    # If already under root, keep
    try:
        path_resolved = path.resolve()
        if PROJECT_ROOT in path_resolved.parents or path_resolved == PROJECT_ROOT:
            return path_resolved
    except Exception:
        pass

    # If writing to a top-level 'Data'/'Backups' outside root, clamp
    name_lower = path.name.lower()
    if name_lower in CLAMP_NAMES:
        return (PROJECT_ROOT / path.name).resolve()

    # If writing inside a folder named Data/Backups outside root, clamp that segment
    for part in path.parts[::-1]:  # iterate from leaf upward
        if part.lower() in CLAMP_NAMES:
            # strip everything up to that segment and re-anchor at root
            try:
                idx = path.parts.index(part)
            except ValueError:
                break
            suffix = Path(*path.parts[idx:])  # e.g., Data\file.csv
            return (PROJECT_ROOT / suffix).resolve()

    # Otherwise keep original absolute path (do not hijack unrelated absolute writes)
    return path


# Patch builtins.open to clamp writes of Data/Backups outside root
_original_open = builtins.open
def _open_wrapper(file, *args, **kwargs):
    mode = kwargs.get("mode") or (args[0] if args else "r")
    # Only clamp on write/append/update modes
    if any(m in str(mode) for m in ("w", "a", "+", "x")):
        file = str(_normalize_target_path(file))
    return _original_open(file, *args, **kwargs)
builtins.open = _open_wrapper  # type: ignore


# Patch os.makedirs and os.mkdir
_original_makedirs = os.makedirs
def _makedirs_wrapper(name, *args, **kwargs):
    name = str(_normalize_target_path(name))
    return _original_makedirs(name, *args, **kwargs)
os.makedirs = _makedirs_wrapper  # type: ignore

_original_mkdir = os.mkdir
def _mkdir_wrapper(name, *args, **kwargs):
    name = str(_normalize_target_path(name))
    return _original_mkdir(name, *args, **kwargs)
os.mkdir = _mkdir_wrapper  # type: ignore


# Patch Path.mkdir
from pathlib import Path as _PathClass
_Path_mkdir_orig = _PathClass.mkdir
def _Path_mkdir(self, *args, **kwargs):
    target = _normalize_target_path(self)
    return _Path_mkdir_orig(target, *args, **kwargs)
_PathClass.mkdir = _Path_mkdir  # type: ignore


# Optional: guard against shutil.copytree creating top-level Backups
try:
    _copytree_orig = shutil.copytree
    def _copytree(src, dst, *args, **kwargs):
        dst = str(_normalize_target_path(dst))
        return _copytree_orig(src, dst, *args, **kwargs)
    shutil.copytree = _copytree  # type: ignore
except Exception:
    pass


# ------------------------ Apply Streamlit patches ------------------------
try:
    import streamlit as st  # noqa: F401
    _patch_streamlit_rerun(st)
    _patch_streamlit_dataframe(st)
except Exception:
    pass

_patch_streamlit_cache_hashing()
