from __future__ import annotations
import streamlit as st
from pathlib import Path
from typing import List
from programs.simple_predict import predict_powerball, predict_megamillions

st.set_page_config(page_title="AstroLotto: Main", layout="wide")
st.title("AstroLotto ▸ Quick Picks")

def _paths_for(game: str) -> List[Path]:
    root = Path(__file__).resolve().parents[2] / "Data"
    if game == "Powerball":
        return [root / "cached_powerball_data.csv", root / "powerball.csv"]
    else:
        return [root / "cached_mega_millions_data.csv", root / "mega_millions.csv", root / "megamillions.csv"]

def render():
    game = st.selectbox("Game", ["Powerball", "Mega Millions"])
    nsets = st.slider("How many sets?", 1, 5, 3)
    if st.button("Generate"):
        picks = []
        if game == "Powerball":
            for _ in range(nsets): picks.append(predict_powerball(_paths_for(game)))
        else:
            for _ in range(nsets): picks.append(predict_megamillions(_paths_for(game)))
        for i, p in enumerate(picks, 1):
            st.write(f"**Set {i}:** {p}")

render()
