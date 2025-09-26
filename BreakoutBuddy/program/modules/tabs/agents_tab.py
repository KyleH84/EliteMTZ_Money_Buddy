from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import streamlit as st
import pandas as pd

def render_agents_tab():
    st.subheader("Agents")
    try:
        from modules.agents.orchestrator import AgentOrchestrator  # may raise
    except Exception as e:
        st.warning("Agents modules not available or failed to import. Configure your 'agents' package if you expect this tab.")
        st.caption(str(e))
        return

    tickers = st.text_input("Tickers (comma/space-separated) for agents").strip()
    pri = st.slider("Prior win prob (default for unknown)", 0.0, 1.0, 0.5, 0.05)
    if st.button("Run agents", type="primary"):
        syms = [t.strip().upper() for t in (tickers.replace(',', ' ').split()) if t.strip()] if tickers else []
        if not syms:
            st.info("Enter at least one ticker.")
            return
        orch = AgentOrchestrator({})
        async def _go():
            priors = {s: pri for s in syms}
            return await orch.run_batch(syms, priors=priors)
        try:
            import asyncio
            df = asyncio.run(_go())
            if isinstance(df, pd.DataFrame) and not df.empty:
                st.dataframe(df, width="stretch", hide_index=True)
            else:
                st.info("No agent outputs.")
        except Exception as e:
            st.error(f"Agent run failed: {e}")
