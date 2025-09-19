# Robust Hot/Cold helpers with special-column detection + logging
from typing import List, Tuple, Optional
import pandas as pd
from pathlib import Path
import re
import datetime as dt

# Try to import detectors if your build provides them
try:
    from utilities.smart_features import detect_white_columns as _detect_white_columns
except Exception:
    _detect_white_columns = None
try:
    from utilities.smart_features import detect_special_column as _detect_special_column
except Exception:
    _detect_special_column = None

LOG_DIR = Path(__file__).resolve().parents[2] / "Data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "hot_cold.log"

def _log(msg: str) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    except Exception:
        pass

DEFAULT_WINDOW = 200

# ---- Column detection ----
def detect_white_columns(df: pd.DataFrame):
    if _detect_white_columns:
        try:
            cols = _detect_white_columns(df)
            if cols:
                return cols
        except Exception:
            pass
    # Fallback: any column like white1..whiteN or n1..nN
    cols = []
    for c in df.columns:
        lc = str(c).lower()
        if re.fullmatch(r"(white|w)\d+", lc) or re.fullmatch(r"n\d+", lc):
            cols.append(c)
    # If still empty, take first 5 numeric-ish columns except special-looking ones
    if not cols:
        numericish = []
        for c in df.columns:
            if str(c).lower() in ("draw_date","date","special","bonus","power","mega","lucky"):
                continue
            s = pd.to_numeric(df[c], errors="coerce")
            if s.notna().sum() >= max(5, int(len(df)*0.2)):
                numericish.append(c)
        cols = numericish[:5]
    return cols

_SPECIAL_NAME_HINTS = [
    "special","bonus","powerball","power","megaball","mega","luckyball","lucky",
    "superball","star","jolly","extra","euro","ball"
]

def detect_special_column(df: pd.DataFrame) -> Optional[str]:
    # Prefer project-provided detector
    if _detect_special_column:
        try:
            col = _detect_special_column(df)
            if col and col in df.columns:
                return col
        except Exception:
            pass
    # Heuristic: look for any column whose name contains a special hint
    best = None
    for c in df.columns:
        lc = str(c).lower()
        for hint in _SPECIAL_NAME_HINTS:
            if hint in lc:
                best = c
                break
        if best:
            break
    return best

# ---- Windowing ----
def _prep_window(df: pd.DataFrame, window: int = DEFAULT_WINDOW) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if "draw_date" in df.columns:
        try:
            dfx = df.copy()
            dfx["__dd"] = pd.to_datetime(dfx["draw_date"], errors="coerce")
            dfx = dfx.sort_values("__dd", ascending=False).drop(columns="__dd")
            return dfx.head(max(int(window), 1))
        except Exception:
            pass
    return df.tail(max(int(window), 1))

# ---- Parsers ----
_LIST_NUM_RE = re.compile(r"\d+")

def _series_to_ints(series: pd.Series) -> pd.Series:
    # Accept values like 7, "7", "[7]", "mega=7", etc.
    s = series.astype(str)
    out = s.apply(lambda x: _LIST_NUM_RE.findall(x))
    out = out.apply(lambda xs: int(xs[0]) if xs else None)
    return pd.to_numeric(out, errors="coerce")

# ---- APIs ----
def hot_cold_white(df: pd.DataFrame, topn: int = 10, window: int = DEFAULT_WINDOW):
    dfx = _prep_window(df, window)
    if dfx.empty:
        return [], []
    cols = detect_white_columns(dfx) or []
    if not cols:
        _log("[hotcold] no white columns detected")
        return [], []
    try:
        vals = pd.concat([pd.to_numeric(dfx[c], errors="coerce") for c in cols], axis=0).dropna().astype(int)
    except Exception:
        # last-resort: try parsing as lists/strings
        try:
            vals = pd.concat([_series_to_ints(dfx[c]) for c in cols], axis=0).dropna().astype(int)
        except Exception:
            _log(f"[hotcold] failed to parse whites from {cols}")
            return [], []
    if vals.empty:
        _log("[hotcold] white values empty after parsing")
        return [], []
    vc = vals.value_counts().sort_values(ascending=False)
    hot = [int(i) for i in vc.index[:max(0,int(topn))].tolist()]
    cold = [int(i) for i in vc.sort_values(ascending=True).index[:max(0,int(topn))].tolist()]
    return hot, cold

def hot_cold_special(df: pd.DataFrame, game: str, topn: int = 10, window: int = DEFAULT_WINDOW):
    dfx = _prep_window(df, window)
    if dfx.empty:
        return [], []
    scol = detect_special_column(dfx)
    if not scol or scol not in dfx.columns:
        _log(f"[hotcold] special column not found for game={game}; cols={list(dfx.columns)}")
        return [], []
    vals = _series_to_ints(dfx[scol]).dropna().astype(int)
    if vals.empty:
        _log(f"[hotcold] special values empty in column {scol}")
        return [], []
    vc = vals.value_counts().sort_values(ascending=False)
    hot = [int(i) for i in vc.index[:max(0,int(topn))].tolist()]
    cold = [int(i) for i in vc.sort_values(ascending=True).index[:max(0,int(topn))].tolist()]
    return hot, cold

# Legacy aliases
get_hot_cold_white = hot_cold_white
get_hot_cold_special = hot_cold_special
