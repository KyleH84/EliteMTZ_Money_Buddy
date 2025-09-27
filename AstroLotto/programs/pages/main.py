from __future__ import annotations

"""
Minimal AstroLotto main page.

This page provides a simple interface for generating lottery number
predictions.  It chooses a game, loads the corresponding cached CSV
history, and invokes the lightweight fallback predictors from
``simple_predict.py``.  The UI allows the user to pick the game and
generate one or more prediction sets on demand.

Note: this minimal implementation does not expose every advanced option
described in the About page (such as agents, oracle gains, diversity
parameters, etc.), but it ensures the app displays predictions rather
than a blank screen.  Additional controls can be layered onto this
foundation as needed.
"""

import streamlit as st
from pathlib import Path
from typing import List

try:
    from AstroLotto.programs.simple_predict import predict_powerball, predict_megamillions  # type: ignore
except Exception:
    # Fallback: import relative to this file in case of packaging variations
    from ..simple_predict import predict_powerball, predict_megamillions  # type: ignore


def _predict(game: str, data_dir: Path) -> dict:
    """Dispatch to the appropriate simple predictor based on game name."""
    game_lower = game.lower().replace(" ", "")
    if game_lower in ("powerball", "powerball", "power ball"):
        path = data_dir / "cached_powerball_data.csv"
        return predict_powerball([path])
    if game_lower in ("mega millions", "megamillions", "mega_millions"):
        path = data_dir / "cached_megamillions_data.csv"
        return predict_megamillions([path])
    # Unknown game
    return {"error": f"Unsupported game: {game}"}


def render() -> None:
    """Render the main AstroLotto predictions page."""
    st.set_page_config(page_title="AstroLotto", layout="wide")
    st.title("AstroLotto Predictions")

    # Determine where the cached CSV files live.  They reside two levels
    # above this file in the Data folder.
    data_dir = Path(__file__).resolve().parents[2] / "Data"
    st.caption(f"Using data directory: {data_dir}")

    # Game selection
    game = st.selectbox("Choose a game", options=["Powerball", "Mega Millions"], index=0)

    # Number of prediction sets to generate
    n_sets = st.number_input(
        "How many sets?", min_value=1, max_value=5, step=1, value=1,
        help="Generate multiple prediction sets for variety."
    )

    if st.button("Predict"):
        with st.spinner("Generating predictions..."):
            results: List[dict] = []
            for _ in range(int(n_sets)):
                res = _predict(game, data_dir)
                results.append(res)
        for i, res in enumerate(results, 1):
            st.subheader(f"Set {i}")
            if "error" in res:
                st.error(res["error"])
            else:
                # Display white balls and special ball nicely
                white_key = "white_balls" if "white_balls" in res else "white"
                special_key = "powerball" if "powerball" in res else ("mega_ball" if "mega_ball" in res else "special")
                whites = res.get(white_key) or res.get("white") or []
                special = res.get(special_key)
                st.write({
                    "Game": game,
                    "White Balls": whites,
                    "Special": special,
                    "Method": res.get("method", "simple")
                })
