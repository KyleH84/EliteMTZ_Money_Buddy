# programs/pages/admin.py — Admin (Tools includes Run Backfill Now)
import streamlit as st
from pathlib import Path
import pandas as pd
import numpy as np
import shutil, time

# Make root importable regardless of run cwd
import sys as _sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in _sys.path:
    _sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Admin", layout="wide")
st.title("Admin")

DATA = ROOT / "Data"
BACKUPS = DATA / "backups"
BACKUPS.mkdir(parents=True, exist_ok=True)

CACHE_MAP = {
    "Mega Millions": "cached_megamillions_data.csv",
    "Powerball": "cached_powerball_data.csv",
    "Colorado Cash 5": "cached_cash5_data.csv",
    "Lucky for Life": "cached_luckyforlife_data.csv",
    "Colorado Lotto+": "cached_colorado_lottery_data.csv",
    "Pick 3": "cached_pick3_data.csv",
}
RULES = {
    "Mega Millions": dict(white_max=70, white_count=5, special_max=25),
    "Powerball": dict(white_max=69, white_count=5, special_max=26),
    "Colorado Cash 5": dict(white_max=32, white_count=5, special_max=None),
    "Lucky for Life": dict(white_max=48, white_count=5, special_max=18),
    "Colorado Lotto+": dict(white_max=40, white_count=6, special_max=None),
    "Pick 3": dict(white_max=9,  white_count=3, special_max=None, pick3=True),
}

ALT_SPECIAL = ["s1","S1","pb","PB","powerball","Powerball","mb","MB","mega_ball","MegaBall","bonus","Bonus","special","Special"]
def ALT_WHITE(i: int):
    return [f"n{i}", f"N{i}", f"w{i}", f"W{i}", f"white{i}", f"White{i}", f"num{i}", f"Num{i}", f"ball{i}", f"Ball{i}", f"d{i}", f"D{i}"]

def _find_col(df: pd.DataFrame, names) -> str | None:
    cols = set(df.columns)
    for n in names:
        if n in cols:
            return n
    norm = {str(c).strip().lower().replace(' ', '').replace('_',''): c for c in df.columns}
    for n in names:
        nn = str(n).strip().lower().replace(' ', '').replace('_','')
        if nn in norm:
            return norm[nn]
    return None

def _validate_game_df(gname: str, path: Path):
    issues = []
    rules = RULES.get(gname, {})
    white_max = int(rules.get("white_max", 70))
    white_count = int(rules.get("white_count", 5))
    special_max = rules.get("special_max", None)
    pick3 = bool(rules.get("pick3", False))
    white_min = 0 if pick3 else 1

    if not path.exists():
        return [f"missing file {path.name}"]

    try:
        df = pd.read_csv(path)
    except Exception as e:
        return [f"cannot read CSV ({e})"]

    if df.empty:
        issues.append("file is empty")

    found_white = []
    for i in range(1, white_count+1):
        col = _find_col(df, ALT_WHITE(i))
        if not col:
            issues.append(f"missing column n{i}")
        else:
            found_white.append(col)

    sp_col = None
    if special_max is not None:
        sp_col = _find_col(df, ALT_SPECIAL)
        if not sp_col:
            issues.append("missing special column s1")

    # ranges
    for col in found_white:
        vals = pd.to_numeric(df[col], errors="coerce")
        bad = vals[(vals < white_min) | (vals > white_max)]
        if bad.any():
            issues.append(f"out-of-range values in {col} (expected {white_min}..{white_max})")

    if (special_max is not None) and (sp_col is not None):
        vals = pd.to_numeric(df[sp_col], errors="coerce")
        bad = vals[(vals < 1) | (vals > int(special_max))]
        if bad.any():
            issues.append(f"out-of-range values in {sp_col} (expected 1..{int(special_max)})")

    # duplicates per row (not pick3)
    if not pick3 and (len(found_white) == white_count) and not df.empty:
        for idx, row in df.iterrows():
            try:
                ws = [int(row[c]) for c in found_white]
            except Exception:
                continue
            if len(ws) != len(set(ws)):
                issues.append(f"row {idx} has duplicate white numbers")
                break
    return issues

def _backup(path: Path) -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    dest = BACKUPS / f"{path.stem}.{ts}{path.suffix}"
    shutil.copy2(path, dest)
    return dest

def _repair_pick3():
    gname = "Pick 3"
    path = DATA / CACHE_MAP[gname]
    msgs = []
    if not path.exists():
        return [f"{gname}: file not found ({path.name})"]
    try:
        bk = _backup(path)
        df = pd.read_csv(path)
        for i, col in enumerate(["n1","n2","n3"], start=1):
            if col not in df.columns:
                for alt in [f"num{i}", f"w{i}", f"d{i}", f"ball{i}"]:
                    if alt in df.columns:
                        df[col] = df[alt]
                        break
                else:
                    df[col] = np.nan
        for col in ["n1","n2","n3"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").round().astype("Int64")
        df = df.dropna(subset=["n1","n2","n3"]).copy()
        for col in ["n1","n2","n3"]:
            df[col] = df[col].clip(lower=0, upper=9).astype(int)
        keep = [c for c in ["date","n1","n2","n3","s1"] if c in df.columns]
        df = df[keep]
        df.to_csv(path, index=False)
        msgs.append(f"pick3: repaired and saved. backup -> {bk.name}")
    except Exception as e:
        msgs.append(f"pick3: repair failed ({e})")
    return msgs

def _fix_duplicate_whites_all():
    logs = []
    for gname, fname in CACHE_MAP.items():
        if gname == "Pick 3":
            continue
        rules = RULES[gname]
        white_count = int(rules.get("white_count", 5))
        path = DATA / fname
        if not path.exists():
            logs.append(f"{gname}: no file")
            continue
        try:
            df = pd.read_csv(path)
        except Exception as e:
            logs.append(f"{gname}: read failed ({e})")
            continue
        cols = []
        for i in range(1, white_count+1):
            c = _find_col(df, ALT_WHITE(i))
            if not c: cols=[]; break
            cols.append(c)
        if len(cols) != white_count:
            logs.append(f"{gname}: skipped (missing white columns)")
            continue
        mask_dup = df.apply(lambda r: len({r[cols[i]] for i in range(len(cols))}) != len(cols), axis=1)
        if mask_dup.any():
            bk = _backup(path)
            df2 = df.loc[~mask_dup].copy()
            df2.to_csv(path, index=False)
            logs.append(f"{gname}: removed {int(mask_dup.sum())} duplicate-row(s). backup -> {bk.name}")
        else:
            logs.append(f"{gname}: no duplicate rows")
    return logs

# ---------- Analytics helpers ----------
def _load_game_df(gname: str):
    fname = CACHE_MAP[gname]
    path = DATA / fname
    if not path.exists():
        return pd.DataFrame(), [], None
    df = pd.read_csv(path)
    white_cols = []
    for i in range(1, int(RULES[gname]["white_count"]) + 1):
        c = _find_col(df, ALT_WHITE(i))
        if c:
            white_cols.append(c)
    sp_col = None
    if RULES[gname].get("special_max") is not None:
        sp_col = _find_col(df, ALT_SPECIAL)
    return df, white_cols, sp_col

def _freq_series(df: pd.DataFrame, white_cols, white_min: int, white_max: int) -> pd.Series:
    if df.empty or not white_cols:
        return pd.Series(dtype=int)
    vals = []
    for c in white_cols:
        arr = pd.to_numeric(df[c], errors="coerce")
        arr = arr[(arr >= white_min) & (arr <= white_max)]
        vals.extend(arr.astype(int).tolist())
    if not vals:
        return pd.Series(dtype=int)
    s = pd.Series(vals).value_counts().sort_index()
    s.name = "count"
    return s

def _draw_date_range(df: pd.DataFrame):
    if "date" not in df.columns:
        return "n/a", "n/a"
    try:
        d = pd.to_datetime(df["date"], errors="coerce").dropna()
        if d.empty:
            return "n/a", "n/a"
        return d.min().date().isoformat(), d.max().date().isoformat()
    except Exception:
        return "n/a", "n/a"

# ---------- Models helpers ----------
def _backtest_frequency(gname: str, lookback: int = 300, horizon: int = 50) -> dict:
    df, white_cols, sp_col = _load_game_df(gname)
    wc = int(RULES[gname]["white_count"])
    white_min = 0 if RULES[gname].get("pick3") else 1
    white_max = int(RULES[gname]["white_max"])
    if df.empty or len(white_cols) < wc:
        return {"error": "not enough data/columns"}
    n = len(df)
    if n < (lookback + horizon + 1):
        lookback = max(wc*10, min(lookback, n//2))
        horizon = max(1, n - lookback - 1)
    train = df.iloc[:n-horizon]
    test = df.iloc[n-horizon:]
    s = _freq_series(train, white_cols, white_min, white_max)
    top = list(s.sort_values(ascending=False).index[:wc])
    matches = []
    for _, row in test.iterrows():
        try:
            actual = [int(row[c]) for c in white_cols]
        except Exception:
            continue
        m = len(set(actual) & set(top))
        matches.append(int(m))
    return {"top": top, "avg_matches": float(np.mean(matches) if matches else 0.0), "distribution": matches, "tested_draws": len(matches)}

try:
    from programs.utilities.per_ball_ml import train_per_ball_ml, predict_per_ball_ml  # type: ignore
except Exception:
    try:
        from utilities.per_ball_ml import train_per_ball_ml, predict_per_ball_ml  # type: ignore
    except Exception:
        train_per_ball_ml = None
        predict_per_ball_ml = None

def _quick_per_ball_ml(gname: str, horizon: int = 50):
    if train_per_ball_ml is None or predict_per_ball_ml is None:
        return {"error": "per_ball_ml module not available"}
    df, white_cols, sp_col = _load_game_df(gname)
    if df.empty:
        return {"error": "no data"}
    try:
        model_pack = train_per_ball_ml(gname.lower().replace(" ", "_"), df, neg_per_pos=4)
        tail = df.tail(min(horizon, len(df)))
        probs = predict_per_ball_ml(tail, model_pack)
        shape = None
        try:
            shape = (len(probs), len(probs[0])) if isinstance(probs, list) else (len(probs),)
        except Exception:
            pass
        return {"status": "trained", "probe_rows": len(tail), "probs_shape": shape}
    except Exception as e:
        return {"error": str(e)}

# ---------- Backfill helpers ----------
def _run_backfill_all():
    results = {}
    runner = None
    try:
        from programs.utilities.backfill_runner_helper import run_backfill_for_csv as _rb  # type: ignore
        runner = _rb
    except Exception:
        try:
            from utilities.backfill_runner_helper import run_backfill_for_csv as _rb  # type: ignore
            runner = _rb
        except Exception:
            runner = None
    if runner is None:
        return {"error": "backfill runner not found (utilities.backfill_runner_helper.run_backfill_for_csv)"}

    for gname, fname in CACHE_MAP.items():
        path = DATA / fname
        try:
            res = runner(str(path), game=gname.lower().replace(" ", "_"))
        except TypeError:
            res = runner(str(path))
        except Exception as e:
            res = {"ok": False, "error": str(e)}
        results[gname] = res
    return results

# ------------------- Tabs -------------------
tab1, tab2, tab3, tab4 = st.tabs(["Data & Health", "Analytics", "Models", "Tools"])

with tab1:
    st.subheader("Cache Status & Repair")
    cols = st.columns(3)
    for i, (gname, fname) in enumerate(CACHE_MAP.items()):
        c = cols[i % 3]
        with c:
            st.markdown(f"**{gname}**")
            p = DATA / fname
            st.code(str(p))
            exists = p.exists()
            rows = 0
            try:
                if exists:
                    rows = max(0, sum(1 for _ in open(p, 'r', encoding='utf-8', errors='ignore')) - 1)
            except Exception:
                pass
            st.json({"exists": exists, "size_bytes": p.stat().st_size if exists else 0, "rows": rows, "note": None})

with tab2:
    st.subheader("Analytics dashboard")
    gname = st.selectbox("Game", list(CACHE_MAP.keys()), index=0, key="analytics_game")
    df, white_cols, sp_col = _load_game_df(gname)
    if df.empty:
        st.warning("No data for this game.")
    else:
        wc = int(RULES[gname]["white_count"])
        white_min = 0 if RULES[gname].get("pick3") else 1
        white_max = int(RULES[gname]["white_max"])
        # Date range
        start, end = _draw_date_range(df)
        st.caption(f"Rows: {len(df)} | Date range: {start} → {end}")
        # Frequency chart (top 15)
        freq = _freq_series(df, white_cols, white_min, white_max)
        if not freq.empty:
            topN = freq.sort_values(ascending=False).head(min(15, len(freq)))
            st.bar_chart(topN)
            st.write(", ".join([f"{int(k)} ({int(v)})" for k, v in topN.items()]))
        else:
            st.info("Could not compute number frequencies (missing columns or empty).")

with tab3:
    st.subheader("Models")
    gname = st.selectbox("Game", list(CACHE_MAP.keys()), index=0, key="models_game")
    colA, colB = st.columns(2)
    with colA:
        st.caption("Baseline backtest (frequency picks)")
        lookback = st.slider("Lookback draws", 100, 1000, 300, 50, key="bt_lookback")
        horizon  = st.slider("Test horizon draws", 20, 200, 50, 10, key="bt_horizon")
        if st.button("Run backtest"):
            res = _backtest_frequency(gname, lookback=lookback, horizon=horizon)
            if "error" in res:
                st.error(res["error"])
            else:
                st.success(f"Avg matches per draw: {res['avg_matches']:.2f} over {res['tested_draws']} draws")
                st.write("Top fixed set:", res["top"])
                st.bar_chart(pd.Series(res["distribution"]).value_counts().sort_index())
    with colB:
        st.caption("Per-ball ML (quick probe)")
        if st.button("Train quick per-ball ML"):
            res = _quick_per_ball_ml(gname)
            if "error" in res:
                st.error(res["error"])
            else:
                st.success("Model trained.")
                st.json(res)

with tab4:
    st.subheader("Maintenance Tools")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.caption("Cache Ops")
        try:
            from programs.features.refresh import refresh_all  # optional in your project
            if st.button("Refresh ALL games"):
                with st.spinner("Refreshing all games..."):
                    res = refresh_all(ROOT)
                st.success("Refresh attempted. See details below.")
                st.json({k: str(v) for k, v in res.items()})
        except Exception:
            if st.button("Refresh ALL games"):
                st.warning("Refresh script not found (programs.features.refresh.refresh_all).")

        if st.button("Run Backfill Now"):
            res = _run_backfill_all()
            if isinstance(res, dict) and res.get("error"):
                st.error(res["error"])
            else:
                st.success("Backfill attempted. See details below.")
                st.json(res)

    with c2:
        st.caption("Health")
        if st.button("Run Smoke Test (ALL games)"):
            for gname, fname in CACHE_MAP.items():
                p = DATA / fname
                issues = _validate_game_df(gname, p)
                st.caption(str(p))
                if issues:
                    st.subheader(gname)
                    st.error(f"{len(issues)} issue(s)")
                    for m in issues:
                        st.write("• " + m)
                else:
                    st.subheader(gname)
                    st.success("OK")

        if st.button("Quick sanity check"):
            counts = {}
            for gname, fname in CACHE_MAP.items():
                p = DATA / fname
                ok = p.exists() and p.stat().st_size > 0
                counts[gname] = "OK" if ok else "missing/empty"
            st.json(counts)

    with c3:
        st.caption("Repairs")
        if st.button("Repair Pick3 file"):
            res = _repair_pick3()
            for m in res:
                st.write("• " + m)
        if st.button("Fix duplicate whites (all games)"):
            logs = _fix_duplicate_whites_all()
            for m in logs:
                st.write("• " + m)


    st.markdown("---")
    st.subheader("Oracle Feeds")
    oc1, oc2 = st.columns(2)
    with oc1:
        if st.button("Refresh Oracle Now"):
            try:
                from programs.utilities.oracle_data import refresh_oracle_now  # type: ignore
            except Exception:
                from utilities.oracle_data import refresh_oracle_now  # type: ignore
            try:
                vals = refresh_oracle_now()
                st.success("Oracle refreshed.")
                st.json(vals)
            except Exception as e:
                st.error(f"Refresh failed: {e}")
    with oc2:
        if st.button("Show Oracle Health"):
            try:
                from programs.utilities.oracle_data import oracle_health  # type: ignore
            except Exception:
                from utilities.oracle_data import oracle_health  # type: ignore
            try:
                vals = oracle_health()
                st.json(vals)
            except Exception as e:
                st.error(f"Health check failed: {e}")
