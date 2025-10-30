# === ADDED: Explain a pick panel with small chart ===
try:
    import streamlit as st
    import pandas as pd
    import numpy as np

    def _explain_block(df: pd.DataFrame) -> None:
        if df is None or df.empty:
            return
        # Ticker chooser
        tickers = sorted(set(df.get("Ticker", df.get("Symbol", pd.Series([], dtype=str)))).astype(str))
        if not tickers:
            return
        with st.expander("📝 Explain a pick", expanded=False):
            sym = st.selectbox("Symbol", tickers, key="watchlist_explain_symbol")
            row = df[df.get("Ticker", df.get("Symbol")) == sym].tail(1)
            if row.empty:
                st.info("No data for selection."); return
            r = row.iloc[-1].to_dict()

            # Simple bullet explanation
            bullets = []
            def num(x, nd=2):
                try:
                    return f"{float(x):,.{nd}f}"
                except Exception:
                    return str(x)
            bullets.append(f"**ChangePct**: {num(r.get('ChangePct', 0))}%")
            bullets.append(f"**RelSPY**: {num(r.get('RelSPY', 0), 3)}")
            bullets.append(f"**RVOL**: {num(r.get('RVOL', 0), 3)}")
            bullets.append(f"**RSI4**: {num(r.get('RSI4', 0))}")
            bullets.append(f"**ConnorsRSI**: {num(r.get('ConnorsRSI', 0))}")
            bullets.append(f"**SqueezeHint**: {r.get('SqueezeHint', 'Off')}")
            st.markdown("\n".join([f"- {b}" for b in bullets]))

            # Small chart (90d) via yfinance if available
            try:
                import yfinance as yf
                data = yf.download(sym, period="90d", interval="1d", progress=False, auto_adjust=False)
                if not data.empty:
                    st.line_chart(data["Close"].rename(sym))
                else:
                    st.info("No recent price data available.")
            except Exception as _e:
                st.info("Chart unavailable.")
except Exception:
    # leave silently if not applicable
    pass
