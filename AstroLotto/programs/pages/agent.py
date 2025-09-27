# AstroLotto/programs/pages/agent.py (patched)
# Fix: TextWidgetsMixin.text_input() got multiple values for argument 'value'
# Cause: passing both positional and keyword 'value'. Use keyword only; unique 'key' per widget.
import streamlit as st

def render():
    st.title("AstroLotto Agent")
    # Example safe usage pattern
    # old: st.text_input("Prompt", prompt, value=prompt)
    # new:
    prompt = st.session_state.get("al_agent_prompt", "Ask about lotto odds...")
    prompt = st.text_input("Prompt", value=prompt, key="al_prompt")
    if st.button("Run", type="primary"):
        st.write("(agent would run here)")