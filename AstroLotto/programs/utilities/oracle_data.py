
# Bridge so `from utilities import oracle_data` works on Streamlit Cloud.
# Delegates to the real module at modules.utilities.oracle_data
from importlib import import_module as _imp
_m = _imp('modules.utilities.oracle_data')
# Re-export public names
for _k in dir(_m):
    if not _k.startswith('__'):
        globals()[_k] = getattr(_m, _k)
# Optionally expose the module too
oracle_data = _m
