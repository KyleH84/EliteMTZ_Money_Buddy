from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Mapping of game identifiers to the module and function used to refresh that game.
# We reference the lower‑case ``programs.services`` package directly; earlier builds
# used ``Program.services``, which was just an alias for the same code.  If you
# maintain a ``Program`` package for backwards compatibility you can still
# point to it here.  See also the Admin page for ad‑hoc refreshes.
GAMES = {
    "megamillions": ("programs.services.mega_updates", "update_megamillions"),
    "powerball": ("programs.services.powerball_updates", "update_powerball"),
    "cash5": ("programs.services.cash5_updates", "update_cash5"),
    "luckyforlife": ("programs.services.lucky_updates", "update_luckyforlife"),
    "colorado": ("programs.services.colorado_updates", "update_colorado"),
    "pick3": ("programs.services.pick3_updates", "update_pick3"),
}

def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent

def _stamp_path(root: Path, key: str) -> Path:
    return (root / "Data" / "cache" / f"last_{key}_refresh.txt")

def _should_refresh(stamp_path: Path, min_hours: float) -> bool:
    try:
        if not stamp_path.exists():
            return True
        t = datetime.fromtimestamp(float(stamp_path.read_text().strip()), tz=timezone.utc)
        return (datetime.now(tz=timezone.utc) - t) >= timedelta(hours=min_hours)
    except Exception:
        return True

def _write_stamp(stamp_path: Path) -> None:
    stamp_path.parent.mkdir(parents=True, exist_ok=True)
    stamp_path.write_text(str(datetime.now(tz=timezone.utc).timestamp()))

def maybe_refresh_caches(min_hours: float = 6.0) -> None:
    root = _project_root()
    for key, (mod_name, func_name) in GAMES.items():
        stamp = _stamp_path(root, key)
        if not _should_refresh(stamp, min_hours):
            continue
        try:
            mod = __import__(mod_name, fromlist=[func_name])
            fn = getattr(mod, func_name, None)
            if fn is None: continue
            res = fn(root)
            _write_stamp(stamp)
            jp = getattr(res, "jackpot_text", None)
            if jp:
                (root / "Data" / "cache" / f"{key}_jackpot.txt").write_text(jp)
        except Exception:
            continue
