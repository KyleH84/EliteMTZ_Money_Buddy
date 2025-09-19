# ui/intentions.py
import streamlit as st
def render_intention_ui():
    st.subheader("Intention (optional)")
    intent = st.text_input("Set your intention (optional)", value=st.session_state.get("intention_text",""))
    st.session_state["intention_text"] = intent
    lucky_str = st.text_input("Lucky whites (comma-separated)", value=",".join(map(str, st.session_state.get("lucky_whites", []))))
    try:
        lucky_whites = [int(x) for x in lucky_str.split(",") if x.strip().isdigit()]
    except Exception:
        lucky_whites = []
    st.session_state["lucky_whites"] = lucky_whites
    special_str = st.text_input("Lucky special balls (comma-separated)", value=",".join(map(str, st.session_state.get("lucky_specials", []))))
    try:
        lucky_specials = [int(x) for x in special_str.split(",") if x.strip().isdigit()]
    except Exception:
        lucky_specials = []
    st.session_state["lucky_specials"] = lucky_specials
