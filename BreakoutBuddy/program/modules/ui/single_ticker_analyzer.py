from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

import io
import pandas as pd
import streamlit as st
from modules import explain as explain_mod
from modules import charting as chart
from modules.services import agents_service as agents_svc

def render(*, settings, analyze_one_fn, friendly_lines_fn, header: bool = True):
    if header:
        st.subheader("Single Ticker Analyzer")
    typed = getattr(settings, "typed_symbol", "") or ""
    col1, col2 = st.columns([3,1])
    with col1:
        tk = st.text_input("Ticker", typed, key="single_ticker_input").strip().upper()
    with col2:
        run = st.button("Analyze", type="primary")
    if not tk:
        st.caption("Enter a ticker to analyze.")
        return
    if not run and getattr(settings, "auto_analyze", True):
        run = True
    if not run:
        return

    with st.spinner(f"Analyzing {tk}…"):
        try:
            one = analyze_one_fn(tk)
            if one is None or len(one) == 0:
                st.warning("No data returned for that symbol.")
                return
            show = [c for c in ["Ticker","Close","ChangePct","RelSPY","ATRpct","RVOL","RSI4","ConnorsRSI","SqueezeHint"] if c in one.columns]
            st.dataframe(one[show] if show else one, width="stretch", hide_index=True)

            # Short & detailed "Why"
            row = None
            try:
                row = one.iloc[0]
            except Exception:
                pass
            short_lines = friendly_lines_fn(row) if row is not None else []
            if short_lines:
                st.markdown("**Why (short):**")
                st.markdown("\n".join(f"- {ln}" for ln in short_lines))

            detailed = explain_mod.explain_ticker_detailed(row) if row is not None else "No detailed explanation."
            with st.expander("Why (detailed)", expanded=True):
                st.text(detailed)
            # Pros & Cons
            st.markdown('**Pros & Cons**')
            c1, c2 = st.columns(2)
            try:
                pros = []
                cons = []
                # derive signals using alphamap helper if available
                try:
                    sigs = explain_mod._describe_signals_with_alphamap(row)
                    pros.extend(sigs)
                except Exception:
                    pass
                # crowding risks
                try:
                    if str(row.get('CrowdRisk','')) == 'High': cons.append('Crowded risk')
                    if str(row.get('RetailChaseRisk','')) == 'High': cons.append('Retail chase risk')
                except Exception:
                    pass
                # momentum / RVOL hints
                try:
                    if float(row.get('RelSPY',0))>0: pros.append('Outperforming SPY')
                    if float(row.get('RVOL',1))>=2: pros.append('High RVOL')
                    if float(row.get('RSI4',50))<10: pros.append('Oversold bounce')
                    if float(row.get('RSI4',50))>80: cons.append('Overbought short-term')
                except Exception:
                    pass
                with c1:
                    if pros:
                        for ptxt in pros[:8]:
                            st.markdown(f'✅ {ptxt}')
                    else:
                        st.caption('No clear tailwinds.')
                with c2:
                    if cons:
                        for ctxt in cons[:8]:
                            st.markdown(f'⚠️ {ctxt}')
                    else:
                        st.caption('No obvious risks flagged.')
            except Exception:
                pass
            try:
                tf = st.selectbox('Chart timeframe', ['1M','3M','6M','1Y'], index=1)
                show_rsi4 = st.checkbox('Overlay RSI(4)', value=True)
                show_crsi = st.checkbox('Overlay ConnorsRSI', value=False)
                chart.render_price_chart(tk, timeframe=tf, show_rsi4=show_rsi4, show_crsi=show_crsi)
            except Exception:
                pass
                # Agent notes (optional, always attempt)
                try:
                    agent_notes = agents_svc.run_agents([tk], priors={})  # may return None
                    if agent_notes:
                        st.markdown("\n**Agent notes:**")
                        st.text(str(agent_notes))
                except Exception:
                    pass

            # --- Export: include short + detailed Why and row snapshot
            buf = io.StringIO()
            buf.write(f"Ticker: {tk}\n\n")
            if row is not None:
                try:
                    sel = {k: row.get(k) for k in ["Close","ChangePct","RelSPY","ATRpct","RVOL","RSI2","RSI4","ConnorsRSI","PctFrom200d","SqueezeHint","P_up"] if k in row}
                    buf.write("Snapshot:\n")
                    for k,v in sel.items(): buf.write(f"- {k}: {v}\n")
                    buf.write("\n")
                except Exception:
                    pass
            if short_lines:
                buf.write("Why (short):\n")
                for ln in short_lines: buf.write(f"- {ln}\n")
                buf.write("\n")
            buf.write("Why (detailed):\n")
            buf.write(detailed + "\n")
            try:
                agent_notes = agents_svc.run_agents([tk], priors={})
                if agent_notes:
                    buf.write("\nAgent notes:\n")
                    buf.write(str(agent_notes) + "\n")
            except Exception:
                pass
            st.download_button("Download analysis.txt", data=buf.getvalue().encode("utf-8"), file_name=f"{tk}_analysis.txt")
        except Exception as e:
            st.error(f"Analysis failed: {e}")
