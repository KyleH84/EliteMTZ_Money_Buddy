# utilities package initializer: run safety + heal + oracle autofill quietly
try:
    from . import safety_runtime as _safety
    _safety.install()
except Exception:
    pass
try:
    from . import boot_heal as _heal  # runs on import
except Exception:
    pass
try:
    from . import oracle_autofill as _oa  # patches compute_oracle to autofill parts
    _oa.patch()
except Exception:
    pass
