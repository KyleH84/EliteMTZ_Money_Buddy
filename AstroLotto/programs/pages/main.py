from __future__ import annotations

import streamlit as st
from pathlib import Path
from typing import List
from programs.simple_predict import predict_powerball, predict_megamillions

ROOT = Path(__file__).resolve().parents[2]

st.title("AstroLotto — Quick Picks")
st.caption("Lightweight fallback predictor so the main page always shows something useful.")

game = st.selectbox("Game", ["Powerball", "Mega Millions"])
nsets = st.slider("How many sets?", 1, 5, 3)

def paths_for(game: str) -> List[Path]:
    data = ROOT / "Data"
    if game == "Powerball":
        return [data / "cached_powerball_data.csv", data / "powerball.csv"]
    else:
        return [data / "cached_mega_millions_data.csv", data / "mega_millions.csv", data / "megamillions.csv"]

if st.button("Generate"):
    paths = paths_for(game)
    picks = []
    if game == "Powerball":
        for _ in range(nsets):
            out = predict_powerball(paths)
            picks.append(out)
    else:
        for _ in range(nsets):
            out = predict_megamillions(paths)
            picks.append(out)

    for i, p in enumerate(picks, 1):
        st.write(f"**Set {i}:** {p}")
