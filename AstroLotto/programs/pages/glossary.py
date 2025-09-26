
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# page_glossary_al.py
import streamlit as st

st.set_page_config(page_title="AstroLotto: Glossary", layout="wide")
st.title("AstroLotto ▸ Glossary")
st.caption("Quick definitions and how each setting affects predictions. Use the search box to jump to terms.")

# --- Search ---
q = st.text_input("Search terms (e.g., 'κ', 'entropy', 'oracle')", value="").strip().lower()

# Helper to render a term
def term(anchor: str, title: str, body: str):
    st.markdown(f'<a name="{anchor}"></a>', unsafe_allow_html=True)
    with st.expander(title, expanded=False):
        st.markdown(body)

# --- Core concepts ---
core = {
    "white-vs-special": (
        "White balls vs Special ball",
        """
**White balls** are the main draw numbers. **Special ball** (Powerball/MegaBall) is drawn from a separate, usually smaller range.  
We keep separate probability vectors for each because they follow different rules and histories.
        """
    ),
    "distribution-W": (
        "W: white-ball distribution",
        """
`W` is a vector of probabilities over all possible white numbers for the next draw. It’s normalized (sums to 1).  
Many features (history, Oracle signals, hot/cold) contribute to `W` before you sample tickets.
        """
    ),
    "distribution-Sp": (
        "Sp: special-ball distribution",
        """
`Sp` is the separate probability vector for the special ball. Like `W`, it is normalized.  
You’ll often see both logged pre/post temporal correction.
        """
    ),
    "entropy": (
        "Entropy (distribution spread)",
        """
Shannon entropy of `W` (or `Sp`). Higher entropy → more even/uncertain; lower entropy → more concentrated bets.  
We log `entropy_W_base`/`entropy_W_final` and the same for `Sp` to show how temporal correction changes concentration.
        """
    ),
}

# --- Temporal helper ---
temporal = {
    "kappa": (
        "κ (Kozyrev coupling strength)",
        """
Scaling factor for the temporal nudge. Larger |κ| = stronger push along the estimated time-sensitivity.  
Start small, use the **Autotune κ** page to find data-driven values.
        """
    ),
    "dt0": (
        "Δt₀ (reference window)",
        """
Reference time window (in seconds). Used in the Kozyrev shift formula to anchor “status quo” vs the forecast window.
        """
    ),
    "dt": (
        "Δt (forecast window)",
        """
Effective time horizon you’re targeting (in seconds) — typically the time until the next draw.  
Changing Δt changes how far the temporal nudge looks ahead.
        """
    ),
    "epsilon": (
        "ε (finite-difference horizon)",
        """
When estimating time-sensitivity dW/dt numerically, we compare `W(t+ε)` vs `W(t-ε)`.  
`ε` is that step size (in **days** in the UI). Larger ε smooths noise; smaller ε reacts to short-term changes.
        """
    ),
    "dtK": (
        "Δt_K (Kozyrev time shift)",
        """
Computed shift used by the correction:  
**Δt_K = κ · h · (1/Δt − 1/Δt₀)**  
It combines your κ with Planck’s constant *h* and the two windows (Δt, Δt₀) into an effective temporal push.
        """
    ),
    "Et": (
        "E_t, E_t0 (time-energy densities)",
        """
Internal diagnostics proportional to **h/Δt** and **h/Δt₀**. They’re reported for transparency and logging, and help explain the magnitude/sign of the shift.
        """
    ),
    "dWdt": (
        "dW/dt (time sensitivity of the distribution)",
        """
Directional derivative of `W` with respect to time, estimated via finite differences.  
The temporal correction applies **(dW/dt) · Δt_K** to nudge `W`, then renormalizes.
        """
    ),
}

# --- Oracle & features ---
oracle = {
    "oracle": (
        "Oracle",
        """
Bundle of cyclical/astral/market/geo signals (e.g., moon phases, Kp index, planetary alignments, volatility proxies).  
In AstroLotto, Oracle contributes a score multiplier and controlled noise (“chaos”) to reflect unknowns.
        """
    ),
    "hot-cold": (
        "Hot/Cold blend",
        """
Empirical bias from recent frequency: “hot” numbers appear more often recently; “cold” appear less.  
You can blend a fraction of hot/cold into the base distribution via **α** and sharpen with **γ** to emphasize extremes.
        """
    ),
    "retro": (
        "Retro-intention",
        """
Optional setting that gives extra weight to numbers that have performed well in the recent past (a short “retro” memory).  
Useful if you believe near-term clustering happens beyond chance.
        """
    ),
    "intention": (
        "Intention bias",
        """
A small, explicit bias from your input text (“intention”) toward certain structures. Kept very small by default to avoid overfitting.
        """
    ),
    "quantum": (
        "Quantum universes & decoherence",
        """
Simulation setting that samples across multiple hypothetical “universes” and blends results with a decoherence factor and observer bias.  
Primarily for exploration; effects are purposely modest.
        """
    ),
}

# --- Logging & autotune ---
logging = {
    "logs": (
        "Logs (Data/temporal_logs.csv)",
        """
One row per run, including κ settings, **Et/Et0/Δt_K**, entropies, and (optionally) JSON-encoded vectors: `W_base`, `W_final`, `Sp_base`, `Sp_final`.  
These allow the autotuner to reconstruct distributions for alternative κ without rerunning the whole pipeline.
        """
    ),
    "objective": (
        "Autotune objective (mass on winners)",
        """
For each logged run, we score the normalized distribution on the actual winning numbers and average across runs.  
The tuner scans a κ grid and selects the κ that **maximizes average mass on winners**.
        """
    ),
    "config": (
        "Config (extras/al_config.json)",
        """
Saved defaults from the autotune page. The main app reads this on startup (unless a session override is set).
        """
    ),
    "session": (
        "Session override (Use best κ now)",
        """
Button on the Autotune page that sets `st.session_state['temporal_kappa_default']` so the main app uses that κ immediately without a restart.
        """
    ),
}

# --- Render sections with optional filtering ---
def render_section(title, items):
    st.subheader(title)
    for anchor, (name, body) in items.items():
        if q and (q not in name.lower() and q not in body.lower() and q not in anchor.lower()):
            continue
        term(anchor, f"{name}", body)

render_section("Core concepts", core)
render_section("Temporal helper", temporal)
render_section("Oracle & features", oracle)
render_section("Logging & autotune", logging)

st.caption("Don’t see a term you need? Open an issue or ping the maintainer — we’ll add it.")