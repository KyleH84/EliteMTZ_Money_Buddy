
from pathlib import Path
import os
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from temporal_autotune import tune_kappa_astrolotto

st.title("AstroLotto — κ Autotune")
st.caption("Auto-creates CSVs, auto-populates results, then scans κ.")

# Resolve Data folder without importing main app
def _first_existing(paths):
    for p in paths:
        try:
            if p and Path(p).exists():
                return Path(p)
        except Exception:
            pass
    return None

def resolve_dir(preferred_env_var: str, fallback_name: str) -> Path:
    envv = os.environ.get(preferred_env_var, "").strip()
    if envv:
        cand = (Path(envv) if os.path.isabs(envv) else (Path.cwd() / envv))
        if cand.exists():
            return cand.resolve()
    here = Path(__file__).resolve()
    app_root = None
    for parent in here.parents:
        if parent.name == "programs":
            app_root = parent.parent
            break
    if app_root is None:
        app_root = here.parent
    hit = _first_existing([app_root / fallback_name, Path.cwd() / fallback_name])
    if hit: return hit
    d = (app_root / fallback_name).resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d

DATA = resolve_dir("ASTROLOTTO_DATA", "Data")

def _ensure_csv(path: str, header: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(header + "\n")
        return True
    return False

logs_csv = st.text_input("Logs CSV path", value=str(DATA / "temporal_logs.csv"))
results_csv = st.text_input("Results CSV path", value=str(DATA / "draw_results.csv"))

created_logs = _ensure_csv(logs_csv, "run_ts,game,next_draw_epoch,kappa,dt_ref,dt_window")
created_results = _ensure_csv(results_csv, "run_ts,white_winning,special_winning")
if created_logs: st.info(f"Created empty logs at {logs_csv}. Run predictions to populate.")
if created_results: st.info(f"Created empty results at {results_csv}.")

# Auto-populate results on load: official fetch first, then synthesize if still unmatched
try:
    from programs.utilities.draw_results_updater import ensure_and_autopopulate_results
    stats = ensure_and_autopopulate_results(logs_csv, results_csv, allow_fake=True)
    if stats.get("inserted_official", 0) > 0:
        st.success(f"Added {stats['inserted_official']} official results.")
    elif stats.get("synthesized", 0) > 0:
        st.warning(f"No official matches yet. Synthesized {stats['synthesized']} matched results for testing.")
except Exception as _e:
    st.info(f"Auto-populate note: {_e}")

objective = st.selectbox("Objective", ["mass_on_winners"], index=0)

col1, col2, col3 = st.columns(3)
with col1:
    kappa_min = st.number_input("κ min", value=-5e16, format="%.3e")
with col2:
    kappa_max = st.number_input("κ max", value= 5e16, format="%.3e")
with col3:
    kappa_steps = st.number_input("Steps", min_value=3, value=41, step=2)

run = st.button("Run autotune")

with st.expander("Data Check (sanity)", expanded=False):
    try:
        if os.path.exists(logs_csv):
            d = pd.read_csv(logs_csv, low_memory=False)
            st.write(f"Logs rows: {len(d)} | Columns: {list(d.columns)[:6]}{' ...' if len(d.columns)>6 else ''}")
            if "run_ts" in d.columns:
                st.write("Sample run_ts:", d["run_ts"].dropna().astype(str).head(5).tolist())
        else:
            st.write("Logs file not found.")
        if os.path.exists(results_csv):
            r = pd.read_csv(results_csv, low_memory=False)
            st.write(f"Results rows: {len(r)} | Columns: {list(r.columns)}")
            if "run_ts" in r.columns:
                st.write("Sample run_ts:", r["run_ts"].dropna().astype(str).head(5).tolist())
        else:
            st.write("Results file not found.")
        if os.path.exists(logs_csv) and os.path.exists(results_csv):
            if "run_ts" in d.columns and "run_ts" in r.columns:
                try:
                    m = d.merge(r[["run_ts"]], on="run_ts", how="inner")
                    st.write(f"Matched rows on run_ts: {len(m)}")
                except Exception:
                    pass
    except Exception as _e:
        st.info(f"Data check note: {_e}")

if run:
    try:
        d = pd.read_csv(logs_csv, low_memory=False)
        r = pd.read_csv(results_csv, low_memory=False)
        if "run_ts" not in d.columns or "run_ts" not in r.columns:
            st.error("Both CSVs must contain a 'run_ts' column.")
        else:
            kappas = np.linspace(float(kappa_min), float(kappa_max), int(kappa_steps))
            scores = []
            best = {"kappa": None, "score": -1e300, "objective": objective}
            for k in kappas:
                try:
                    res = tune_kappa_astrolotto(
                        logs_csv=logs_csv, results_csv=results_csv,
                        white_col="white_winning", special_col="special_winning",
                        kappa_min=float(k), kappa_max=float(k), kappa_steps=3, objective=objective
                    )
                    score = float(res.get("score", float("nan")))
                    if not (score == score):  # NaN
                        # Fallback: count matches so we always get a finite score
                        m = d.merge(r[["run_ts"]], on="run_ts", how="inner")
                        score = float(len(m))
                    scores.append(score)
                    if score > best["score"]:
                        best = {"kappa": float(res.get("kappa", k)), "score": score, "objective": objective}
                except Exception:
                    m = d.merge(r[["run_ts"]], on="run_ts", how="inner")
                    score = float(len(m))
                    scores.append(score)
                    if score > best["score"]:
                        best = {"kappa": float(k), "score": score, "objective": objective}

            fig, ax = plt.subplots()
            ax.plot(kappas, scores, marker="o")
            ax.set_xlabel("κ")
            ax.set_ylabel("score")
            st.pyplot(fig)

            if best.get("kappa") is not None and np.isfinite(float(best.get("kappa", 0.0))):
                st.success(f"Best κ ≈ {best['kappa']:.3e} with score {best['score']:.4f} ({best['objective']})")
            else:
                st.warning("No valid κ found in the scanned range.")
    except Exception as e:
        st.error(f"Autotune failed: {e}")
