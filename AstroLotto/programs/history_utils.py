# History utilities for AstroLotto (frequency, gaps, heatmaps, pairs, triplets, streaks, time-window filter)
from __future__ import annotations
from pathlib import Path
from typing import Tuple, List, Optional
import numpy as np, pandas as pd

def project_root_from_page(file_path: str) -> Path:
    """Return the project root directory given the path to a page module.

    Pages live two levels beneath the project root in the
    ``programs/pages`` directory.  Earlier versions searched for a
    capitalised ``Program`` directory; on case‑sensitive systems this
    fails if only the lower‑case ``programs`` package exists.  This
    implementation climbs the directory tree until it finds a folder
    named either ``programs`` or ``Program`` (case‑insensitive) and
    returns its parent.  As a fallback, if no such folder is found it
    returns two levels up from the supplied file path.
    """
    p = Path(file_path).resolve()
    q = p
    while q.parent != q:
        if q.name.lower() in ("programs", "program"):
            return q.parent
        q = q.parent
    # Fallback: assume file is ``programs/pages/<page>.py`` and return
    # the grandparent directory.  This mirrors the earlier behaviour
    # where the project root was two levels up from the page file.
    return p.parent.parent

def load_cached_dataframe(root: Path, game_key: str) -> pd.DataFrame:
    paths = {
        "powerball": root / "Data" / "cached_powerball_data.csv",
        "megamillions": root / "Data" / "cached_megamillions_data.csv",
        "cash5": root / "Data" / "cached_cash5_data.csv",
        "luckyforlife": root / "Data" / "cached_luckyforlife_data.csv",
        "colorado": root / "Data" / "cached_colorado_lottery_data.csv",
        "pick3": root / "Data" / "cached_pick3_data.csv",
    }
    path = paths.get(game_key)
    if not path or not path.exists():
        raise FileNotFoundError(f"Cached data for {game_key!r} not found at {path}")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    if "draw_date" in df.columns:
        try: df["draw_date"] = pd.to_datetime(df["draw_date"])
        except Exception: pass
    return df

def extract_numbers(df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
    white_cols = [c for c in df.columns if c.startswith("white")]
    n_cols = [c for c in df.columns if (c.startswith("n") and c[1:].isdigit())]
    if white_cols:
        cols = sorted(white_cols, key=lambda x: int(x.replace("white","")))
    elif n_cols:
        cols = sorted(n_cols, key=lambda x: int(x[1:]))
    else:
        guess = [c for c in df.columns if c in ("num1","num2","num3","num4","num5","num6")]
        cols = guess or []
    if not cols:
        raise ValueError("Could not detect number columns in dataframe.")
    arr = df[cols].to_numpy(dtype=float)
    arr = arr[~np.isnan(arr).any(axis=1)]
    return arr.astype(int), cols

def number_range_for_game(game_key: str, arr: Optional[np.ndarray] = None) -> int:
    ranges = {"powerball":69,"megamillions":70,"cash5":32,"luckyforlife":48,"colorado":40,"pick3":10}
    if game_key in ranges: return ranges[game_key]
    if arr is not None: return int(np.nanmax(arr))
    return 70

def frequency_table(arr: np.ndarray, max_n: int) -> pd.DataFrame:
    flat = arr.flatten()
    counts = np.bincount(flat, minlength=max_n+1)[1:max_n+1]
    idx = np.arange(1, max_n+1)
    df = pd.DataFrame({"number": idx, "count": counts})
    df["rank"] = df["count"].rank(method="dense", ascending=False).astype(int)
    return df.sort_values(["count","number"], ascending=[False, True]).reset_index(drop=True)

def position_heatmap(arr: np.ndarray, max_n: int) -> np.ndarray:
    positions = arr.shape[1]
    heat = np.zeros((positions, max_n), dtype=int)
    for pos in range(positions):
        col = arr[:, pos]
        for n in col:
            if 1 <= n <= max_n: heat[pos, n-1] += 1
    return heat

def gap_distribution(arr: np.ndarray, max_n: int) -> pd.DataFrame:
    last_seen = {n: None for n in range(1, max_n+1)}
    gaps = []
    for i, row in enumerate(arr):
        seen_now = set(row.tolist())
        for n in range(1, max_n+1):
            if n in seen_now:
                if last_seen[n] is not None: gaps.append(i - last_seen[n])
                last_seen[n] = i
    s = pd.Series(gaps) if gaps else pd.Series([], dtype=float)
    return s.value_counts().sort_index().rename_axis("gap").reset_index(name="count") if not s.empty else pd.DataFrame({"gap":[], "count":[]})

def top_pairs(arr: np.ndarray, top_k: int = 20):
    from collections import Counter
    c = Counter()
    for row in arr:
        row = sorted(set(row.tolist()))
        for i in range(len(row)):
            for j in range(i+1, len(row)):
                c[(row[i], row[j])] += 1
    items = sorted(c.items(), key=lambda x: (-x[1], x[0]))
    if not items: import pandas as pd; return pd.DataFrame({"pair":[], "count":[]})
    pairs = [f"{a}-{b}" for (a,b),_ in items[:top_k]]
    counts = [cnt for _, cnt in items[:top_k]]
    import pandas as pd; return pd.DataFrame({ "pair":pairs, "count":counts })

def top_triplets(arr: np.ndarray, top_k: int = 20):
    from collections import Counter
    c = Counter()
    for row in arr:
        row = sorted(set(row.tolist()))
        L = len(row)
        for i in range(L):
            for j in range(i+1, L):
                for k in range(j+1, L):
                    c[(row[i], row[j], row[k])] += 1
    items = sorted(c.items(), key=lambda x: (-x[1], x[0]))
    if not items: import pandas as pd; return pd.DataFrame({"triplet":[], "count":[]})
    trip = [f"{a}-{b}-{c}" for (a,b,c),_ in items[:top_k]]
    counts = [cnt for _, cnt in items[:top_k]]
    import pandas as pd; return pd.DataFrame({ "triplet":trip, "count":counts })

def compute_streaks(arr: np.ndarray, max_n: int) -> pd.DataFrame:
    draws = [set(r.tolist()) for r in arr]
    seen = {n: [] for n in range(1, max_n+1)}
    for s in draws:
        for n in range(1, max_n+1):
            seen[n].append(1 if n in s else 0)
    hot, cold = [], []
    for n, seq in seen.items():
        r = 0; m1 = 0; m0 = 0; r0 = 0
        for v in seq:
            if v: r += 1; m1 = max(m1, r); r0 = 0
            else: r0 += 1; m0 = max(m0, r0); r = 0
        hot.append((n, m1)); cold.append((n, m0))
    import pandas as pd
    return pd.DataFrame(hot, columns=["number","longest_hot"]).merge(pd.DataFrame(cold, columns=["number","longest_cold"]), on="number")

def filter_time_window(df: pd.DataFrame, days: Optional[int]) -> pd.DataFrame:
    if not days or "draw_date" not in df.columns: return df
    cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=int(days))
    return df[df["draw_date"] >= cutoff].reset_index(drop=True)
