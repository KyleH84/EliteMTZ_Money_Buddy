# Sidebar UI for jackpots (live fetch + overrides)
import streamlit as st
from . import jackpots as jp

def render_sidebar(st_obj=None, config=None):
    st = st_obj or __import__("streamlit")
    with st.sidebar.expander("Jackpots (Live/Override)", expanded=False):
        cols = st.columns(2)
        with cols[0]:
            if st.button("Refresh now"):
                for g in ["powerball","megamillions","colorado"]:
                    jp.get_jackpot(g, force_refresh=True)
                st.success("Refreshed.")
        with cols[1]:
            st.caption("Overrides take priority over live fetch.")
        for game,label in [("powerball","Powerball"),("megamillions","MegaMillions"),("colorado","Colorado Lotto+")]:
            live = jp.get_jackpot(game) or 0
            st.write(f"**{label}**: ${live:,}" if live else f"**{label}**: (no data)")
            with st.popover(f"Set override for {label}"):
                val = st.number_input("Override amount ($)", min_value=0, step=1_000_000, value=int(live or 0), key=f"ov_{game}")
                c1, c2 = st.columns(2)
                if c1.button("Save override", key=f"save_{game}"):
                    jp.set_override(game, int(val))
                    st.success("Saved override.")
                if c2.button("Clear override", key=f"clear_{game}"):
                    jp.clear_override(game)
                    st.info("Cleared override.")
