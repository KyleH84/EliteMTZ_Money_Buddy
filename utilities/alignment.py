from __future__ import annotations
# Bridge module so `utilities.alignment` works in Cloud or local
try:
    from AstroLotto.programs.utilities.alignment import *  # type: ignore
except Exception as _e:
    # If AstroLotto package path isn’t available yet, make a best-effort relative import
    from . import alignment as _shadow  # type: ignore
    for _n in dir(_shadow):
        if not _n.startswith('_'):
            globals()[_n] = getattr(_shadow, _n)
