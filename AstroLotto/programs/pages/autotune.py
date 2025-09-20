
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)


# page_autotune_al.py
import streamlit as st
import os
import numpy as np
import matplotlib.pyplot as plt
from temporal_autotune import tune_kappa_astrolotto

st.set_page_config(page_title="AstroLotto: Autotune κ", layout="wide")
st.title("AstroLotto ▸ Autotune κ (Kozyrev coupling)")

st.markdown("Use logged runs and draw results to pick a κ that maximizes your chosen objective.")

logs_csv = st.text_input("Logs CSV path", value="Data/temporal_logs.csv")
results_csv = st.text_input("Results CSV path", value="Data/draw_results.csv")
objective = st.selectbox("Objective", ["mass_on_winners"], index=0)

col1, col2, col3 = st.columns(3)
with col1:
    kappa_min = st.number_input("κ min", value=-5e16, format="%.3e")
with col2:
    kappa_max = st.number_input("κ max", value= 5e16, format="%.3e")
with col3:
    kappa_steps = st.number_input("Steps", min_value=3, value=41, step=2)

run = st.button("Run autotune")

if run:
    try:
        # Run scan and also compute curve
        import pandas as pd
        from temporal_autotune import _safe_json, _normalize  # internal helpers are okay for page use

        d = pd.read_csv(logs_csv)
        r = pd.read_csv(results_csv)
        # Merge minimally to get aligned rows for curve; the tuner will do full logic again for best pick.
        m = d.merge(r[["run_ts","white_winning","special_winning"]], on="run_ts", how="inner")

        kappas = np.linspace(kappa_min, kappa_max, int(kappa_steps))
        scores = []
        # Use the tuner in a loop to ensure consistent scoring logic:
        for k in kappas:
            res = tune_kappa_astrolotto(
                logs_csv=logs_csv,
                results_csv=results_csv,
                kappa_min=k, kappa_max=k, kappa_steps=1,
                objective=objective
            )
            scores.append(res.get("objective", float("nan")))

        best = tune_kappa_astrolotto(
            logs_csv=logs_csv,
            results_csv=results_csv,
            kappa_min=kappa_min, kappa_max=kappa_max, kappa_steps=int(kappa_steps),
            objective=objective
        )
        st.success(f"Best κ ≈ {best['kappa']:.3e}  |  objective = {best['objective']:.6f}")

        fig = plt.figure()
        plt.plot(kappas, scores, marker='o')
        plt.xlabel("κ")
        plt.ylabel(objective)
        plt.title("Objective vs κ")
        st.pyplot(fig)

        st.caption("Tip: rerun after you log more draws with different κ values.")
    except Exception as e:
        st.error(f"Autotune failed: {e}")


import json
cfg_path = "Data/al_config.json"
if run and 'best' in locals():
    if st.button("Save best κ as default"):
        try:
            os.makedirs("Data", exist_ok=True)
            with open(cfg_path, "w",encoding="utf-8") as f:
                json.dump({"best_kappa": best["kappa"], "objective": best["objective"]}, f, indent=2)
            st.success(f"Saved to {cfg_path}")
        except Exception as e:
            st.error(f"Save failed: {e}")
