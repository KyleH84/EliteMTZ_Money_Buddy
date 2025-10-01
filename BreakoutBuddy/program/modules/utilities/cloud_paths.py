from __future__ import annotations
# Re-export specific APIs from program.utilities.cloud_paths to satisfy modules.* import paths
try:
    from BreakoutBuddy.program.utilities.cloud_paths import resolve_data_dir  # noqa: F401
except Exception as e:
    # Fallback: import as a module and alias
    import importlib
    _mod = importlib.import_module('BreakoutBuddy.program.utilities.cloud_paths')
    resolve_data_dir = getattr(_mod, 'resolve_data_dir')
__all__ = ['resolve_data_dir']
