from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Program/pages/00_About.py
import json
from pathlib import Path
from datetime import datetime
import streamlit as st

# Try to use the app's config helper if available for ROOT detection
ROOT = None
try:
    from utilities.config import ROOT as _ROOT
    ROOT = _ROOT
except Exception:
    ROOT = Path(__file__).resolve().parents[2]

st.set_page_config(page_title="About AstroLotto", layout="wide")
st.title("About AstroLotto v14.6")

st.markdown(
    """
**What this is**  
AstroLotto is a Streamlit app that learns from lottery history and suggests number picks.
This v14.6 release consolidates the interface down to **APP**, **About** and **Admin** pages while
maintaining the robust data hygiene features introduced in earlier versions.  It includes a
  full **Backfill Engine**, a **Schema Sanity** check and improved **Smart Predictors** (including
ensemble and Monte Carlo options).  The heavier analytics pages have been removed or archived to
keep the sidebar focused.  Instead you will find a streamlined Admin page offering data
refreshes, model training and diagnostic tools.
"""
)

with st.expander("How it fits together", expanded=True):
    st.markdown(
        """
**Runtime layout**
- `Data/cached_*_data.csv` – canonical draw history (per game)
- `Data/models/` – trained model artifacts
- `Data/logs/` – app/training logs
- `Data/reports/` – evaluation reports (e.g., `model_eval_<game>.json`)
- `Data/*_predictions.csv` – appended prediction history
- `Extras/requirements.txt` – Python deps for the app
- Launchers: `PC-RUN_AstroLotto.bat` (Windows), `run_astro_app.command` (macOS)
"""
    )

with st.expander("Feature overview"):
    st.markdown(
        """
* **Backfill Engine (all games):** populates/updates cached history for Powerball, Mega Millions,
  Colorado Lotto+, Cash 5, Pick 3 and Lucky for Life.
* **Schema Sanity:** verifies and lightly fixes cache columns on startup (e.g. Pick 3 `d1..d3`).
* **Smart Predictors:** choose between ensemble, Monte Carlo or fallback predictors; the app always
  returns valid number sets.
* **Hot/Cold & History Views:** quick stats from the cached draw files (via the App page).
* **Admin Tools:** check cache health, refresh draws, train models and run maintenance tasks.
"""
    )

with st.expander("Quick start / First‑time setup", expanded=False):
    st.markdown(
        """
1. **Install Python and dependencies** (preferably in a virtual environment).  At the command
   line run:
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate    # Windows
   pip install -r extras/requirements.txt
   ```
2. **Launch the app:**  
   - **Windows:** double‑click `Launch_AstroLotto.bat`  
   - **macOS/Linux:** run `chmod +x Launch_AstroLotto.command` (first run), then double‑click.
3. **Backfill:** open the App page and use the sidebar to click **Run backfill now** to fetch and normalize history.
4. **Schema check:** the app performs a schema sanity check at startup; if it reports issues, re‑run backfill from the sidebar.
5. **(Optional) Train models & evaluate:** visit the Admin page to refresh caches, train models and view evaluation snapshots.
"""
    )

# Show current user prefs if present (kept for visibility, keys may vary by build)
prefs_path = ROOT / "Extras" / "user_prefs.json"
prefs = {}
try:
    prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
except Exception:
    pass

with st.expander("Current settings (Extras/user_prefs.json)"):
    if prefs:
        st.json(prefs)
    else:
        st.info("user_prefs.json not found yet. Defaults will be used.")

with st.expander("Tips & troubleshooting"):
    st.markdown(
        """
* **Nothing opens / port busy?** You can launch the app manually: `streamlit run programs/app_main.py --server.port 8502`.
* **`streamlit` not found?** Activate your virtualenv or reinstall dependencies: `pip install -r extras/requirements.txt`.
* **Pick 3 errors about `d1`?** Running backfill and the schema check will create `d1..d3` from `n1..n3`.
* **Scraper hiccups?** Click **Run backfill now** again; providers occasionally change.
* **Where are files?** See *How it fits together* above for a description of the data directories.
"""
    )

st.caption(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} from {prefs_path} (if present).")
