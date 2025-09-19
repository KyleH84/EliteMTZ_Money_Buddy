from __future__ import annotations
import os, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

try:
    import streamlit as st
    cache_fn = st.cache_data
except Exception:
    # Fallback no-op cache decorator
    def cache_fn(*args, **kwargs):
        def deco(f):
            return f
        return deco

GAME_MAP: Dict[str, Dict[str, Any]] = {
    "powerball": {"white_cols": ["white_1","white_2","white_3","white_4","white_5"], "special": True, "special_col": "powerball", "white_min": 1, "white_max": 69, "special_min": 1, "special_max": 26},
    "mega_millions": {"white_cols": ["white_1","white_2","white_3","white_4","white_5"], "special": True, "special_col": "mega_ball", "white_min": 1, "white_max": 70, "special_min": 1, "special_max": 25},
    "cash5": {"white_cols": ["white_1","white_2","white_3","white_4","white_5"], "special": False, "white_min": 1, "white_max": 32},
    "lucky_for_life": {"white_cols": ["white_1","white_2","white_3","white_4","white_5"], "special": True, "special_col": "lucky_ball", "white_min": 1, "white_max": 48, "special_min": 1, "special_max": 18},
    "colorado_lottery": {"white_cols": ["white_1","white_2","white_3","white_4","white_5","white_6"], "special": False, "white_min": 1, "white_max": 40},
    "pick3": {"white_cols": ["d1","d2","d3"], "special": False, "white_min": 0, "white_max": 9},
}

def _read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig","utf-8","cp1252","latin1"):
        try: return pd.read_csv(path, encoding=enc)
        except Exception: continue
    return pd.read_csv(path, errors="ignore")

def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", "_", str(c).strip().lower()) for c in df.columns]
    return df

_NUM_PAT = re.compile(r"\d+")
def _parse_winning_numbers_cell(cell: Any) -> Optional[List[int]]:
    if cell is None: return None
    s = str(cell).strip()
    if not s or s.lower() in {"nan","none"}: return None
    nums = [int(x) for x in _NUM_PAT.findall(s)]
    return nums if len(nums) >= 5 else None

def _coerce_int(x) -> Optional[int]:
    try:
        if pd.isna(x): return None
    except Exception: pass
    try: return int(str(x).strip())
    except Exception: return None

def _pick_columns(df: pd.DataFrame, game_key: str) -> pd.DataFrame:
    info = GAME_MAP.get(game_key, {})
    whites = info.get("white_cols", [])
    special = info.get("special", False)
    scol = info.get("special_col", "special")
    work = _normalize_headers(df)

    white_syns = [
        ["white_1","white1","w1","wb1","n1","ball_1","ball1","b1","num1","first"],
        ["white_2","white2","w2","wb2","n2","ball_2","ball2","b2","num2","second"],
        ["white_3","white3","w3","wb3","n3","ball_3","ball3","b3","num3","third"],
        ["white_4","white4","w4","wb4","n4","ball_4","ball4","b4","num4","fourth"],
        ["white_5","white5","w5","wb5","n5","ball_5","ball5","b5","num5","fifth"],
        ["white_6","white6","w6","wb6","n6","ball_6","ball6","b6","num6","sixth"],
    ]
    special_syns = [scol,"mega_ball","megaball","mega","mb","powerball","pb","special","lucky_ball","luckyball","lb"]

    out = pd.DataFrame()
    found = {}
    for idx, candidates in enumerate(white_syns, start=1):
        for name in candidates:
            if name in work.columns:
                found[f"white_{idx}"] = work[name]; break
    if found: out = pd.DataFrame(found)

    if special:
        for name in special_syns:
            if name in work.columns: out[scol] = work[name]; break

    if out.empty:
        for alt in ("winning_numbers","winning_number","numbers","winning_nums","winning"):
            if alt in work.columns:
                parsed = work[alt].apply(_parse_winning_numbers_cell)
                expanded = parsed.apply(lambda lst: lst if isinstance(lst, list) else [None]*6)
                needed_whites = len(whites) if whites else 5
                rows = []
                for vals in expanded:
                    vals = list(vals) if isinstance(vals, list) else []
                    row = {}
                    for i in range(1, needed_whites+1):
                        row[f"white_{i}"] = vals[i-1] if len(vals) >= i else None
                    if special:
                        row[scol] = vals[needed_whites] if len(vals) > needed_whites else None
                    rows.append(row)
                out = pd.DataFrame(rows); break

    if not out.empty:
        for c in out.columns: out[c] = out[c].apply(_coerce_int)
    if out.empty: return pd.DataFrame()
    essential = [c for c in out.columns if c.startswith("white_")]
    if essential: out = out.dropna(subset=essential, how="any")
    return out.drop_duplicates().reset_index(drop=True)

def _find_history_files(game_key: str, search_root: Path) -> List[Path]:
    root = Path(search_root or ".")
    globs: List[str] = []
    if game_key == "mega_millions":
        globs = ["**/cached_mega_millions*_data.csv","**/mega_millions*_history*.csv","**/megamillions*_history*.csv","**/mega*_millions*draw*.csv","**/mega*_millions*result*.csv","**/*mega*million*draw*.csv","**/*mega*million*history*.csv","**/*mega*million*result*.csv","**/cached_mega*.csv"]
    elif game_key == "powerball":
        globs = ["**/cached_powerball*_data.csv","**/*powerball*history*.csv","**/*powerball*draw*.csv","**/*powerball*result*.csv","**/cached_power*.csv"]
    else:
        g = game_key.replace(" ", "_")
        globs = [f"**/cached_{g}_data.csv", f"**/{g}*_history*.csv", f"**/{g}*draw*.csv", f"**/{g}*result*.csv", f"**/*{g}*history*.csv"]

    paths: List[Path] = []
    for pattern in globs:
        for p in root.glob(pattern):
            name = p.name.lower()
            if "prediction" in name: continue
            if name.endswith(".csv"): paths.append(p)
    seen, uniq = set(), []
    for p in paths:
        rp = p.resolve()
        if rp not in seen: seen.add(rp); uniq.append(p)
    return uniq

@cache_fn(ttl=900)
def load_history(game_key: str, root_dir: str | Path | None = None) -> pd.DataFrame:
    preferred = os.environ.get("ASTRO_DATA_DIR")
    search_root = Path(preferred) if preferred else Path(root_dir or ".")
    files = _find_history_files(game_key, search_root)
    info = GAME_MAP.get(game_key, {})
    expected_cols = list(info.get("white_cols", []))
    if info.get("special", False): expected_cols.append(info.get("special_col", "special"))
    if not files: return pd.DataFrame(columns=expected_cols)

    for f in files:
        try:
            raw = _read_csv_any(f)
            norm = _pick_columns(raw, game_key)
            if norm is not None and not norm.empty:
                raw_norm = _normalize_headers(raw)
                for dcol in ["draw_date","date","drawdate","draw_time","draw"]:
                    if dcol in raw_norm.columns:
                        try:
                            dt = pd.to_datetime(raw_norm[dcol], errors="coerce")
                            norm.insert(0, "date", dt); norm = norm.sort_values("date").reset_index(drop=True)
                            break
                        except Exception: pass
                return norm[expected_cols] if all(c in norm.columns for c in expected_cols) else norm
        except Exception: continue
    return pd.DataFrame(columns=expected_cols)

def build_features(game_key: str, root_dir: Path | str, target: str = "white") -> Tuple[pd.DataFrame, Optional[pd.Series]]:
    root_dir = Path(root_dir)
    df = load_history(game_key, root_dir)
    if df is None or df.empty: return pd.DataFrame(), None
    num_cols = [c for c in df.columns if c.startswith("white_")]
    if "special" in df.columns: num_cols.append("special")
    for c in num_cols: df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    if "date" in df.columns: df = df.sort_values("date").reset_index(drop=True)
    for c in [x for x in num_cols if x != "special"]:
        df[f"{c}_lag1"] = df[c].shift(1); df[f"{c}_lag7"] = df[c].shift(7)
    if "special" in df.columns: df["special_lag1"] = df["special"].shift(1)
    df_feat = df.dropna().copy()
    y = None
    if target == "white":
        whites = [c for c in num_cols if c.startswith("white_")]
        if whites: y = df_feat[whites[0]].astype("Int64")
    elif target == "special" and "special" in df_feat.columns:
        y = df_feat["special"].astype("Int64")
    drop_cols = []
    if target == "white" and "white_1" in df_feat.columns: drop_cols.append("white_1")
    if target == "special" and "special" in df_feat.columns: drop_cols.append("special")
    X = df_feat.drop(columns=drop_cols, errors="ignore")
    return X, y
