# utilities/backfill_runner_helper.py — Patch 3.1b
# Provides a resilient run_backfill_for_csv used by the audit/fix/fill page.
from __future__ import annotations
from pathlib import Path
import importlib, inspect
import pandas as pd  # type: ignore

def _detect_game_from_name(name: str) -> str | None:
    n = name.lower()
    if "powerball" in n: return "powerball"
    if "mega" in n and "million" in n: return "megamillions"
    if "cash5" in n or "cash_5" in n: return "cash5"
    if "lucky" in n and "life" in n: return "lucky_for_life"
    if "colorado" in n and "lotto" in n: return "colorado_lottery"
    if "pick3" in n: return "pick3"
    return None

def _safe_len_csv(path: Path) -> int:
    try:
        import pandas as _pd  # type: ignore
        df = _pd.read_csv(path)
        return len(df.index)
    except Exception:
        return 0

def run_backfill_for_csv(csv_path: str | Path, game: str | None = None, **kwargs):
    """
    Tries to dispatch to any available backfill function; if none found,
    returns gracefully (ok=True, added_rows=0).
    Compatible with older callers that only expect the call to not crash.
    """
    p = Path(csv_path)
    game = game or _detect_game_from_name(p.name) or ""
    before = _safe_len_csv(p)

    # Try Program.historical_backfill if present
    candidates = [
        ("historical_backfill", "run_backfill_for_csv"),
        ("historical_backfill", "backfill_for_csv"),
        ("historical_backfill", "backfill_game_to_csv"),
        ("historical_backfill", "backfill_csv"),
        ("historical_backfill", "fill_missing_draws"),
        ("historical_backfill", "ensure_history_csv"),
    ]

    used = None
    for mod_name, fn_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, fn_name, None)
            if fn is None:
                continue
            # Try various common signatures
            sig = inspect.signature(fn)
            try:
                if len(sig.parameters) == 2:
                    try:
                        fn(game, str(p))
                        used = f"{mod_name}.{fn_name}(game, path)"
                        break
                    except TypeError:
                        fn(str(p), game)
                        used = f"{mod_name}.{fn_name}(path, game)"
                        break
                elif len(sig.parameters) == 1:
                    fn(str(p))
                    used = f"{mod_name}.{fn_name}(path)"
                    break
                else:
                    # best effort call with kwargs
                    fn(path=str(p), game=game, **kwargs)
                    used = f"{mod_name}.{fn_name}(**kwargs)"
                    break
            except Exception:
                # Continue to next candidate
                continue
        except Exception:
            continue

    after = _safe_len_csv(p)
    added = max(0, after - before)
    return {"ok": True, "game": game, "path": str(p), "added_rows": added, "used": used}
