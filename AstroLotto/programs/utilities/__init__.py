# Bridge so imports like `from utilities.x import ...` resolve to modules.utilities.x
import importlib, sys
def __getattr__(name: str):
    modname = f"modules.utilities.{name}"
    m = importlib.import_module(modname)
    sys.modules[f"{__name__}.{name}"] = m
    return m
