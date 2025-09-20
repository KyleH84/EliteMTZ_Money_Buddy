
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

from pathlib import Path

# ---------- Strict per-app Data/Extras resolver (BreakoutBuddy) ----------
from pathlib import Path
import os, sys
BB_HERE     = Path(__file__).resolve()
BB_APP_ROOT = BB_HERE.parents[1]   # .../BreakoutBuddy

def _bb_cloud_roots():
    h = Path.home()
    return [
        h / "OneDrive",
        h / "OneDrive - Personal",
        h / "OneDrive - Wagstaff Law Firm",
        h / "Dropbox",
        h / "Google Drive",
        h / "Library" / "CloudStorage" / "OneDrive",
        h / "Library" / "CloudStorage" / "Dropbox",
        h / "Library" / "CloudStorage" / "GoogleDrive",
    ]

def _bb_first_existing(paths):
    for p in paths:
        try:
            p2 = Path(p).expanduser().resolve()
            if p2.exists():
                return p2
        except Exception:
            pass
    return None

def bb_resolve_dir(preferred_env_var: str, fallback_name: str):
    """
    Strict per-app order (NO repo-level fallback):
      1) Env var (abs or relative)
      2) BB_APP_ROOT/<name>
      3) CWD/<name>
      4) Cloud roots: <BreakoutBuddy>/<name>
      5) Create BB_APP_ROOT/<name>
    """
    envv = os.environ.get(preferred_env_var, "").strip()
    if envv:
        cand = (Path(envv) if os.path.isabs(envv) else (Path.cwd() / envv))
        if cand.exists():
            return cand.resolve()

    hit = _bb_first_existing([BB_APP_ROOT / fallback_name, Path.cwd() / fallback_name])
    if hit:
        return hit

    cands = []
    for root in _bb_cloud_roots():
        cands += [
            root / BB_APP_ROOT.name / fallback_name,
            root / "Projects" / BB_APP_ROOT.name / fallback_name,
        ]
    hit = _bb_first_existing(cands)
    if hit:
        return hit

    target = (BB_APP_ROOT / fallback_name).resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target

BB_DATA   = bb_resolve_dir("BREAKOUTBUDDY_DATA",   "Data")
BB_EXTRAS = bb_resolve_dir("BREAKOUTBUDDY_EXTRAS", "extras")

bb_extras_src = (BB_EXTRAS / "src")
if bb_extras_src.exists() and str(bb_extras_src) not in sys.path:
    sys.path.insert(0, str(bb_extras_src))
# ---------- end resolver ----------

# page_autotune_bb.py
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import os, json, time

from temporal_autotune import tune_kappa_breakoutbuddy

st.set_page_config(page_title="BreakoutBuddy: Autotune κ", layout="wide")
st.title("BreakoutBuddy ▸ Autotune κ (Kozyrev coupling)")
st.caption("Scan κ using your bb_temporal_logs + outcomes. Save to config or apply immediately to this session.")

LOGS_DEFAULT = str(BB_DATA / 'bb_temporal_logs.csv')
OUT_DEFAULT = str(BB_DATA / 'bb_outcomes.csv')
CFG_DEFAULT = "extras/bb_config.json"

def _load_cfg(path=CFG_DEFAULT, fallback=0.0):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return float(json.load(f).get("kappa", fallback))
    except Exception:
        pass
    return float(fallback)

def _save_cfg(kappa: float, meta: dict | None = None, path=CFG_DEFAULT) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {"kappa": float(kappa), "updated_at": int(time.time())}
        if isinstance(meta, dict):
            payload.update(meta)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return True
    except Exception:
        return False

with st.sidebar:
    st.header("Run settings")
    logs_csv = st.text_input("Logs CSV", value=LOGS_DEFAULT)
    outcomes_csv = st.text_input("Outcomes CSV", value=OUT_DEFAULT)
    label_col = st.text_input("Outcome label column", value="label")
    metric = st.selectbox("Metric", ["logloss","auc","mse"], index=0)

    st.divider()
    st.subheader("κ scan")
    kappa_min = st.number_input("κ min", value=-5e16, format="%.3e")
    kappa_max = st.number_input("κ max", value= 5e16, format="%.3e")
    kappa_steps = st.number_input("Steps", min_value=3, value=41, step=2)

    run = st.button("Run autotune", type="primary")

if run:
    try:
        kappas = np.linspace(kappa_min, kappa_max, int(kappa_steps))
        scores = []
        for k in kappas:
            res = tune_kappa_breakoutbuddy(
                logs_csv=logs_csv,
                outcomes_csv=outcomes_csv,
                label_col=label_col,
                kappa_min=k, kappa_max=k, kappa_steps=1,
                metric=metric
            )
            scores.append(res.get("metric"))

        best = tune_kappa_breakoutbuddy(
            logs_csv=logs_csv,
            outcomes_csv=outcomes_csv,
            label_col=label_col,
            kappa_min=kappa_min, kappa_max=kappa_max, kappa_steps=int(kappa_steps),
            metric=metric
        )
        st.success(f"Best κ ≈ {best['kappa']:.3e}  |  {metric} = {best['metric']:.6f}")

        fig = plt.figure()
        plt.plot(kappas, scores, marker='o')
        plt.xlabel("κ")
        plt.ylabel(metric)
        plt.title(f"{metric} vs κ")
        st.pyplot(fig)

        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("Use best κ now (this session)"):
                st.session_state["bb_temporal_kappa_default"] = float(best["kappa"])
                st.success(f"Set session κ default → {best['kappa']:.3e}. Switch to the main page to use it.")
        with colB:
            if st.button("Save best κ to config"):
                meta = {
                    "metric": metric,
                    "metric_value": float(best.get("metric", 0.0)),
                    "scan": {"kappa_min": float(kappa_min), "kappa_max": float(kappa_max), "kappa_steps": int(kappa_steps)},
                    "label_col": label_col
                }
                ok = _save_cfg(float(best["kappa"]), meta=meta)
                if ok:
                    st.success(f"Saved to {CFG_DEFAULT}")
                else:
                    st.error("Failed to save config.")
        with colC:
            if st.button("Reload κ from config"):
                k = _load_cfg()
                st.session_state["bb_temporal_kappa_default"] = float(k)
                st.info(f"Reloaded κ default from config: {k:.3e}")

        st.caption("Tip: seed logs with multiple κ values (including 0) for a reliable fit.")
    except Exception as e:
        st.error(f"Autotune failed: {e}")

st.divider()
st.subheader("Current defaults")
st.write(f"Config κ (if present): **{_load_cfg():.3e}**")
st.write(f"Session κ default (if set): **{st.session_state.get('bb_temporal_kappa_default', None)}**")
