# utilities/io_routing.py — route CSV writes to Data and READ fallback
from __future__ import annotations
import os, re, builtins
from pathlib import Path

_PATTERNS = [
    re.compile(r'.*_predictions\.csv$', re.I),
    re.compile(r'cached_.*_data\.csv$', re.I),
    re.compile(r'.*history.*\.csv$', re.I),
    re.compile(r'.*draw.*\.csv$', re.I),
    re.compile(r'.*result.*\.csv$', re.I),
    re.compile(r'.*mega.*million.*\.csv$', re.I),
    re.compile(r'.*powerball.*\.csv$', re.I),
    re.compile(r'.*cash5.*\.csv$', re.I),
    re.compile(r'.*lucky.*life.*\.csv$', re.I),
    re.compile(r'.*colorado.*lotto.*\.csv$', re.I),
    re.compile(r'.*pick3.*\.csv$', re.I),
]

def _data_dir() -> Path:
    return Path(os.environ.get('ASTRO_DATA_DIR', 'Data'))

def _should_route_write(file, mode: str) -> bool:
    if not any(c in mode for c in ('w','a','x')):
        return False
    p = Path(str(file))
    if str(p.parent) not in ('', '.'):
        return False
    return any(pat.match(p.name) for pat in _PATTERNS)

def _try_read_fallback(file, mode: str) -> str | None:
    # Only for reads, and only if file not found and bare name
    if 'r' not in mode: return None
    p = Path(str(file))
    if str(p.parent) not in ('', '.'): return None
    where = _data_dir() / p.name
    if where.exists(): return str(where)
    return None

def _route_write_path(name: str) -> str:
    d = _data_dir(); d.mkdir(parents=True, exist_ok=True)
    return str(d / name)

def install() -> None:
    _orig_open = builtins.open
    def _open(file, mode='r', *args, **kwargs):
        try:
            if _should_route_write(file, mode):
                file = _route_write_path(Path(str(file)).name)
            else:
                alt = _try_read_fallback(file, mode)
                if alt is not None: file = alt
        except Exception:
            pass
        return _orig_open(file, mode, *args, **kwargs)
    builtins.open = _open
