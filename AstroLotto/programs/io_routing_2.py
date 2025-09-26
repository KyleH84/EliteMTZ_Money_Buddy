from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# utilities/io_routing.py — v3.3
# Forward-looking routing for CSVs & backups:
# - WRITES: Any CSV aimed at Program/, data/, csv/, csvs/, datasets/, or backups/ → Data/ (backups → Data/backups/)
# - READS: Fallback to Data/ (and Data/backups/) if file not found
# - mkdir: Redirect creation of those dirs to Data/ so stray folders aren't created in root/Program
import os, re, builtins
from pathlib import Path

# ---- Config / names ----
_BACKUP_NAMES = {"backup", "backups", "_backups", "bkup", "bkups", "bkp"}
_DATA_ALIAS   = {"data", "dataset", "datasets", "csv", "csvs"}
_PROGRAM_NAMES = {"program"}  # first-segment names that should really be under Data when CSVs are written

_CSV_PATTERNS = [
    re.compile(r'.*\.csv$', re.I),  # we only touch CSVs
]

def _root_dir() -> Path:
    # Prefer env, fall back to this file's grandparent: Program/utilities/ -> ROOT
    env = os.environ.get("ASTRO_ROOT")
    if env:
        try: return Path(env)
        except Exception: pass
    return Path(__file__).resolve().parents[2]

def _data_dir() -> Path:
    env = os.environ.get('ASTRO_DATA_DIR')
    if env:
        try: return Path(env)
        except Exception: pass
    return _root_dir() / "Data"

def _is_rel(p: Path) -> bool:
    try:
        return not p.is_absolute() and not str(p).startswith((f"{PROJECT_DIR}/data/\\\\", "/"))
    except Exception:
        return True

def _is_csv_name(name: str) -> bool:
    return any(pat.match(name) for pat in _CSV_PATTERNS)

def _first_index_in(p: Path, name_set: set[str], max_depth: int | None = None) -> int:
    parts = p.parts
    depth = len(parts) if max_depth is None else min(len(parts), max_depth)
    for i in range(depth):
        comp = parts[i].strip(f"{PROJECT_DIR}/data/").strip().strip(".").lower()
        if comp in name_set:
            return i
    return -1

# ---- Routing decisions ----
def _should_route_write(file, mode: str) -> bool:
    if not any(c in mode for c in ('w','a','x')):
        return False
    p = Path(str(file))
    if not _is_csv_name(p.name):
        return False

    # Already within Data? leave as-is
    try:
        d = _data_dir().resolve()
        if _is_rel(p):
            pass
        else:
            if str(Path(p).resolve()).lower().startswith(str(d).lower() + os.sep):
                return False
    except Exception:
        pass

    # CASE A: relative paths
    if _is_rel(p):
        parent0 = (p.parts[0].lower() if p.parts else "")
        if parent0 in _BACKUP_NAMES:
            return True
        if parent0 in _DATA_ALIAS:
            return True
        if parent0 in _PROGRAM_NAMES:
            return True
        if len(p.parts) == 1:
            # bare CSV in CWD
            return True
        return False

    # CASE B: absolute paths under ROOT
    try:
        root = _root_dir().resolve()
        rp = Path(p).resolve()
        if str(rp).lower().startswith(str(root).lower() + os.sep):
            # If under backups anywhere
            if _first_index_in(rp, _BACKUP_NAMES) >= 0:
                return True
            # If under a data-alias near the top (root/data/, root/csvs/, etc.)
            if _first_index_in(rp.relative_to(root), _DATA_ALIAS, max_depth=2) >= 0:
                return True
            # If under Program/ (common offender during "check for updates")
            if _first_index_in(rp.relative_to(root), _PROGRAM_NAMES, max_depth=2) >= 0:
                return True
    except Exception:
        pass

    return False

def _route_write_path(orig: Path) -> str:
    d = _data_dir()
    root = _root_dir()
    parts = list(orig.parts)

    # Default target is Data/<basename>
    target = d / orig.name

    # Relative routing by first segment
    if _is_rel(orig):
        if parts:
            head = parts[0].strip(f"{PROJECT_DIR}/data/").strip().strip(".").lower()
            tail = Path(*parts[1:]) if len(parts) > 1 else Path("")
            if head in _BACKUP_NAMES:
                target = d / "backups" / tail
            elif head in _DATA_ALIAS:
                target = d / tail
            elif head in _PROGRAM_NAMES:
                target = d / tail
            else:
                target = d / orig.name
    else:
        # Absolute under ROOT: mirror tail after the alias folder
        try:
            rp = orig.resolve()
            if str(rp).lower().startswith(str(root).lower() + os.sep):
                rel = rp.relative_to(root)
                # backups → Data/backups/<tail after backups>
                bi = _first_index_in(rel, _BACKUP_NAMES)
                if bi >= 0:
                    tail = Path(*rel.parts[bi+1:]) if len(rel.parts) > bi+1 else Path("")
                    target = d / "backups" / tail
                else:
                    # data-alias → Data/<tail after alias>
                    ai = _first_index_in(rel, _DATA_ALIAS, max_depth=2)
                    if ai >= 0:
                        tail = Path(*rel.parts[ai+1:]) if len(rel.parts) > ai+1 else Path("")
                        target = d / tail
                    else:
                        # Program → Data/<tail after Program>
                        pi = _first_index_in(rel, _PROGRAM_NAMES, max_depth=2)
                        if pi >= 0:
                            tail = Path(*rel.parts[pi+1:]) if len(rel.parts) > pi+1 else Path("")
                            target = d / tail
        except Exception:
            pass

    target.parent.mkdir(parents=True, exist_ok=True)
    return str(target)

def _try_read_fallback(file, mode: str) -> str | None:
    if 'r' not in mode:
        return None
    p = Path(str(file))

    # If already exists, use it
    try:
        if Path(p).exists():
            return None
    except Exception:
        pass

    d = _data_dir()
    root = _root_dir()

    # Relative reads
    if _is_rel(p):
        parts = list(p.parts)
        if not parts:
            return None
        head = parts[0].strip(f"{PROJECT_DIR}/data/").strip().strip(".").lower()
        tail = Path(*parts[1:]) if len(parts) > 1 else Path(p.name)
        if head in _BACKUP_NAMES:
            cand = d / "backups" / tail
            if cand.exists(): return str(cand)
        if head in _DATA_ALIAS:
            cand = d / tail
            if cand.exists(): return str(cand)
        if head in _PROGRAM_NAMES:
            cand = d / tail
            if cand.exists(): return str(cand)
        # bare name
        cand = d / p.name
        if cand.exists(): return str(cand)
        return None

    # Absolute under ROOT
    try:
        rp = Path(p).resolve()
        if str(rp).lower().startswith(str(root).lower() + os.sep):
            rel = rp.relative_to(root)
            bi = _first_index_in(rel, _BACKUP_NAMES)
            if bi >= 0:
                tail = Path(*rel.parts[bi+1:]) if len(rel.parts) > bi+1 else Path("")
                cand = d / "backups" / tail
                if cand.exists(): return str(cand)
            ai = _first_index_in(rel, _DATA_ALIAS, max_depth=2)
            if ai >= 0:
                tail = Path(*rel.parts[ai+1:]) if len(rel.parts) > ai+1 else Path("")
                cand = d / tail
                if cand.exists(): return str(cand)
            pi = _first_index_in(rel, _PROGRAM_NAMES, max_depth=2)
            if pi >= 0:
                tail = Path(*rel.parts[pi+1:]) if len(rel.parts) > pi+1 else Path("")
                cand = d / tail
                if cand.exists(): return str(cand)
            # bare: try Data/<basename>
            cand = d / rp.name
            if cand.exists(): return str(cand)
    except Exception:
        pass

    return None

# ---- Public installer ----
def install() -> None:
    # open() routing
    _orig_open = builtins.open
    def _open(file, mode='r', *args, **kwargs):
        try:
            p = Path(str(file))
            if _should_route_write(p, mode):
                file = _route_write_path(p)
            else:
                alt = _try_read_fallback(p, mode)
                if alt is not None:
                    file = alt
        except Exception:
            pass
        return _orig_open(file, mode, *args, **kwargs)
    builtins.open = _open

    # mkdir routing: os.makedirs and Path.mkdir
    import os as _os_mod
    _orig_makedirs = _os_mod.makedirs
    def _route_dirpath(path: str | os.PathLike) -> str:
        p = Path(path)
        # If this is a backups/data-alias/Program dir under ROOT or relative, push under Data
        d = _data_dir(); root = _root_dir()
        if _is_rel(p):
            parts = p.parts
            if parts:
                head = parts[0].strip(f"{PROJECT_DIR}/data/").strip().strip(".").lower()
                tail = Path(*parts[1:]) if len(parts) > 1 else Path("")
                if head in _BACKUP_NAMES:
                    return str((d / "backups" / tail))
                if head in _DATA_ALIAS or head in _PROGRAM_NAMES:
                    return str((d / tail))
        else:
            try:
                rp = p.resolve()
                if str(rp).lower().startswith(str(root).lower() + os.sep):
                    rel = rp.relative_to(root)
                    bi = _first_index_in(rel, _BACKUP_NAMES)
                    if bi >= 0:
                        tail = Path(*rel.parts[bi+1:]) if len(rel.parts) > bi+1 else Path("")
                        return str(d / "backups" / tail)
                    ai = _first_index_in(rel, _DATA_ALIAS, max_depth=2)
                    if ai >= 0:
                        tail = Path(*rel.parts[ai+1:]) if len(rel.parts) > ai+1 else Path("")
                        return str(d / tail)
                    pi = _first_index_in(rel, _PROGRAM_NAMES, max_depth=2)
                    if pi >= 0:
                        tail = Path(*rel.parts[pi+1:]) if len(rel.parts) > pi+1 else Path("")
                        return str(d / tail)
            except Exception:
                pass
        return str(p)

    def makedirs_wrapper(name, mode=0o777, exist_ok=False):
        try:
            name = _route_dirpath(name)
        except Exception:
            pass
        return _orig_makedirs(name, mode=mode, exist_ok=exist_ok)
    _os_mod.makedirs = makedirs_wrapper

    _orig_path_mkdir = Path.mkdir
    def path_mkdir_wrapper(self, mode=0o777, parents=False, exist_ok=False):
        try:
            new = Path(_route_dirpath(self))
        except Exception:
            new = self
        return _orig_path_mkdir(new, mode=mode, parents=parents, exist_ok=exist_ok)
    Path.mkdir = path_mkdir_wrapper
