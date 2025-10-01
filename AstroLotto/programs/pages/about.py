from __future__ import annotations


from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import streamlit as st

st.set_page_config(page_title="About AstroLotto", layout="wide")
APP_VERSION = "v17"
st.title(f"About AstroLotto {APP_VERSION}")
st.caption("This page is your owner’s manual. Plain English first, deep detail after.")

# ──────────────────────────────────────────────────────────────────────────────
# OVERVIEW
# ──────────────────────────────────────────────────────────────────────────────
st.header("What is AstroLotto? (Simple Overview)")
st.markdown(
    """
    **AstroLotto** is a lottery “probability weather” app. It blends three things:
    1. **History** of past draws (base frequencies, hot/cold patterns)
    2. **Models** (per‑ball ML and rules) that learn positional tendencies
    3. **Context** (moon phase, geomagnetic activity, market fear proxy, planetary alignments, and optional “quantum/retrocausal” knobs)

    The app turns all of that into one **probability surface** for the white balls and the special ball, then samples from it to propose sets.
    You can keep it conservative or let the weirder signals move the needle. Your call.
    """
)

st.header("Quick Start")
st.markdown(
    """
    1. Pick your **game** from the sidebar.
    2. Leave defaults as‑is and click **Predict** to get one best set.
    3. Use **Rainbow ×3** if you want more variety.
    4. Curious? Turn on **Oracle** and bump the gain a bit (1.5–2.0). Re‑run.
    5. If sets look too similar, raise **Exploration temp** and **Shortlist K**, and keep **Min diff** > 0.
    6. Happy? Save or copy your sets. Done.
    """
)

# ──────────────────────────────────────────────────────────────────────────────
# HOW IT WORKS
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("How picks are made (the short version)", expanded=False):
    st.markdown(
        """
        1) **Per‑ball view**: Each white‑ball position (1st, 2nd, …) and the special ball are modeled separately.
        2) **Base layer**: Historical frequencies → **W_base**, **Sp_base**.
        3) **Model layer**: Optional per‑ball ML and simple rules nudge probabilities.
        4) **Oracle layer**: Moon/Kp/flares/VIX/alignments apply multiplicative weights.
        5) **Quantum/Exploration**: Add controlled randomness so sets aren’t clones.
        6) **EV‑aware filter**: Avoid ultra‑popular “herd” patterns that split payouts.
        7) **Diversity checks**: Enforce minimum differences between sets and specials.
        8) **Shortlist + sample**: Build a shortlist (the top mass) and sample your sets.
        """
    )
    st.caption("Result: one blended **W_final** (white) and **Sp_final** (special) that we sample from, plus readable reasons.")

# ──────────────────────────────────────────────────────────────────────────────
# AGENTS
# ──────────────────────────────────────────────────────────────────────────────
st.header("Agents (What they are & what they do)")
st.markdown(
    """
    **Agents** are small components that look at the same probability surface from different angles and suggest adjustments.
    Examples:
    - **Baseline agent** — keeps you grounded in historical stats.
    - **ML agent** — learns positional quirks from labeled history.
    - **Oracle agent** — reads moon/Kp/flares/VIX/alignments and proposes multipliers.
    - **Quantum agent** — injects controlled exploration and “worldline” variety.
    - **Retro agent** — applies a tunable Kozyrev coupling (**κ**) to favor picks that would have looked “better” under logged deltas.

    You can enable/disable agents with toggles, and you can control how strongly they influence the final weights.
    """
)

# ──────────────────────────────────────────────────────────────────────────────
# CONTROLS — OPTIONS & TOGGLES
# ──────────────────────────────────────────────────────────────────────────────
st.header("All Options & Toggles (What they mean & when to use them)")

with st.expander("Base & Per‑Ball Modeling"):
    st.subheader("Base frequency blend")
    st.markdown(
        """
        Uses plain historical frequencies to create **W_base** and **Sp_base**. This keeps you anchored.
        **When to use:** Always on; it’s the floor other layers adjust.
        """
    )
    st.subheader("Per‑ball ML (opt_per_ball / opt_per_ball_ml)")
    st.markdown(
        """
        Trains simple models per white‑ball position and for the special ball. ML captures positional effects and patterns history misses.
        - **On**: If your data is healthy and you want a modest uplift.
        - **Off**: If you have very sparse history or you prefer pure frequency‑based picks.
        """
    )
    st.caption("If ML fails or data is empty, the app degrades gracefully to base/rules.")

with st.expander("Sacred / Archetype hints"):
    st.markdown(
        """
        Lightweight nudges based on archetypal or numerological patterns. Fun, not overbearing.
        - **Use sacred**: Applies gentle weights tied to typical numerology buckets.
        - **Use archetype**: Similar, with a different mapping set.
        **Tip:** Keep gains modest; treat these as seasoning, not the meal.
        """
    )

with st.expander("Oracle (external context): moon, Kp, flares, VIX, alignments"):
    st.markdown(
        """
        When **Oracle** is enabled, the app computes multipliers from external context:
        - **Moon phase / illumination** — strength varies across phases.
        - **Kp index / geomagnetic** — stronger disturbances can increase chaos.
        - **Solar flares (M/X counts)** — recent activity nudges exploration/weights.
        - **VIX proxy / market fear** — fear/stress can favor “spread‑out” choices.
        - **Planetary alignments** — conjunction/opposition rates tweak clusters.

        **Oracle gain (1.0–2.5 typical)** — how strongly these signals move probabilities.
        - **Lower (≤1.3)**: conservative
        - **Medium (1.5–2.0)**: noticeable effect
        - **High (≥2.2)**: let space‑weather steer the wheel
        """
    )

with st.expander("Quantum / Exploration layer"):
    st.markdown(
        """
        Controls for variety and de‑cloning:
        - **Universes** — number of simulated “worldlines.” More = smoother averages, less variance.
        - **Decoherence** — how quickly worldlines “agree.” Lower → more variety; higher → more convergence.
        - **Observer bias** — pushes towards peaks you “intend.” Keep small if you want neutrality.
        - **QRNG** — optional quantum‑seeded randomness (if available); else uses high‑quality PRNG.

        **When to use:** If your sets look too similar or you want controlled exploration. Start with modest decoherence reductions before cranking temperature.
        """
    )

with st.expander("Retrocausal influence (κ, Δt)"):
    st.markdown(
        """
        Adds a tiny nudge derived from logged delta vectors as if outcomes can inform the present (a speculative, opt‑in toy).
        - **κ (kappa)** — coupling strength. Use **Autotune** page to scan and pick a reasonable value.
        - **Δt horizon** — how far back (or forward window) the deltas are “remembered.”
        - **Memory** — decay factor. Higher = longer memory.

        **When to use:** Only if you’re comfortable with speculative knobs. Keep κ small and verify on the Autotune curve.
        """
    )

with st.expander("Shortlist, Temperature, Diversity, EV aware"):
    st.subheader("Shortlist K")
    st.markdown("How wide the candidate pool is before sampling. Larger K = more variety, but can dilute precision.")
    st.subheader("Exploration temperature")
    st.markdown("Raises sampling entropy. If sets are near-duplicates, increase temperature a bit.")
    st.subheader("Min diff between sets / Unique specials")
    st.markdown("Forces separation so you don’t get clones. Useful when generating multiple sets.")
    st.subheader("EV‑aware unpopular‑combo mode")
    st.markdown(
        """
        Tries to avoid ultra‑popular human patterns (like all low numbers, sequences, straight lines).
        Good for improving expected value by reducing split risk. Doesn’t change hit odds, but can help net outcomes.
        """
    )

with st.expander("User inputs & Lucky numbers"):
    st.markdown(
        """
        - **Name / Birthdate** — used for optional numerology/archetype nudges.
        - **Lucky whites / specials** — lets you bias towards or require certain numbers.
        Keep these optional; they can reduce variety if over‑used.
        """
    )

# ──────────────────────────────────────────────────────────────────────────────
# PAGES / TABS
# ──────────────────────────────────────────────────────────────────────────────
st.header("Pages & Tabs (What you can do)")

with st.expander("Predictions (main)"):
    st.markdown(
        """
        - **Predict ×1** — produces a single “most likely” set using your current blend.
        - **Rainbow ×3** — generates three diverse high‑quality sets (higher exploration + diversity).
        - **Why these** — human‑readable reasons: shortlist nudges, oracle impact, EV hints.
        - **Clear Predictions** — clears history for a fresh run.
        """
    )

with st.expander("Admin → Data & Health, Tools, Training, Jackpots"):
    st.markdown(
        """
        **Data & Health**: shows CSV presence/sizes and last refresh times. Run **Backfill now** if history is thin.

        **Tools**: Refresh caches, Pick3 repair, Oracle feed checks, smoke tests.

        **Training**: “Train all games (per‑ball ML)” runs quick retrains; logs are written for inspection.

        **Jackpots**: pulls next draw info and jackpot sizes (internet required).
        """
    )

with st.expander("Autotune κ"):
    st.markdown(
        """
        Scans κ over a range and plots a score curve (e.g., mass on winners). Use it to select a sane κ for **Retro**.

        **Files**:

        - `Data/temporal_logs.csv` — created automatically if missing; populated by running predictions.

        - `Data/draw_results.csv` — your ground‑truth draw outcomes file.

        **Workflow**: run predictions → collect logs → keep draw results updated → Autotune → (optionally) save best κ.

        """
    )

with st.expander("Glossary"):
    st.markdown(
        """
        See the **Glossary** page for precise definitions of: κ (kappa), Δt, dt_K, entropy, oracle, decoherence, observer bias,
        shortlist K, exploration temperature, EV‑aware, and more.
        """
    )

# ──────────────────────────────────────────────────────────────────────────────
# PRACTICAL RECIPES
# ──────────────────────────────────────────────────────────────────────────────
st.header("Practical Recipes")

with st.expander("Conservative (anchored)"):
    st.markdown(
        """
        - Oracle off or gain ≤ 1.3

        - Per‑ball ML on

        - Universes medium, Decoherence higher, Temperature low

        - EV‑aware on, Diversity moderate

        - Shortlist K modest (not too wide)"""
    )

with st.expander("Oracle‑forward (let space‑weather move the needle)"):
    st.markdown(
        """
        - Oracle on, gain ~1.7–2.2

        - Per‑ball ML on

        - Universes medium, Decoherence medium‑low, Temperature medium

        - EV‑aware on, Diversity moderate

        - Shortlist K wider"""
    )

with st.expander("Rainbow variety (3 sets, clearly different)"):
    st.markdown(
        """
        - Temperature up a notch

        - Shortlist K wider

        - Min diff between sets > 0 and Unique specials on

        - EV‑aware on"""
    )

# ──────────────────────────────────────────────────────────────────────────────
# TROUBLESHOOTING
# ──────────────────────────────────────────────────────────────────────────────
st.header("Troubleshooting & Tips")
st.markdown(
    """
    - **Sets look too similar**: raise **Exploration temp**, **Shortlist K**, and **Min diff**; enable **Unique specials**.

    - **Feels too random**: lower **Decoherence** and **Temperature**; lower **Oracle gain**; reduce Shortlist K.

    - **ML errors or empty**: run **Backfill now** and **Refresh ALL caches**, then retrain.

    - **Autotune won’t run**: ensure `Data/temporal_logs.csv` and `Data/draw_results.csv` exist. The logs file is auto‑created; results you must maintain.

    - **Jackpots not showing**: verify internet and inspect `programs/utilities/jackpots.py` provider list.

    """
)

# ──────────────────────────────────────────────────────────────────────────────
# FILE MAP (for power users)
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("Project map (where things live)"):
    st.code(
        "Data/                      # CSVs, caches, artifacts\n"
        "extras/                    # extra assets and optional libs\n"
        "programs/app_main.py       # Main app (predictions UI)\n"
        "programs/pages/admin.py    # Admin tools & health\n"
        "programs/pages/autotune.py # κ scanning and save\n"
        "programs/pages/about.py    # This manual\n"
        "programs/pages/glossary.py # Terms & symbols",
        language="text",
    )
