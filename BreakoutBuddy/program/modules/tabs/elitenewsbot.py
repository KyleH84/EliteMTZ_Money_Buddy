from __future__ import annotations
from typing import List
from pathlib import Path
import time
import pandas as pd
import streamlit as st

from BreakoutBuddy.program.modules.data import list_universe
from BreakoutBuddy.program.modules.services import news_free, newswire_local

# Resolve default CSV location (program-level Extras/ if available, else Data/)
def _default_csv_path() -> Path:
    here = Path(__file__).resolve()
    # prefer program/extras
    p = here.parents[3] / "extras" / "elite_news.csv"
    if p.exists() or p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    # fallback repo-root Data/
    data_dir = here.parents[4] / "Data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "elite_news.csv"

def _fetch_titles_for(symbols: List[str], per_symbol: int, delay_sec: float) -> pd.DataFrame:
    rows = []
    prog = st.progress(0.0, text=f"Scanning {len(symbols)} tickers for news in last 12h...")
    for i, sym in enumerate(symbols, 1):
        titles = news_free.get_titles(sym, limit=per_symbol)
        for t in titles:
            rows.append({"Date": pd.Timestamp.utcnow(), "Company": "", "Ticker": sym, "Sign": "", "Headline": t, "Link": "", "Source": "yfinance"})
        prog.progress(i/len(symbols), text=f"{i}/{len(symbols)} scanned")
        if delay_sec > 0:
            time.sleep(delay_sec)
    prog.empty()
    df = pd.DataFrame(rows)
    return df

def render_elitenewsbot_tab(*, settings=None):
    st.subheader("EliteNewsBot")

    # Controls
    universe_size = int(st.slider("Universe size (scan up to N tickers)", min_value=10, max_value=1000, value=250, step=10, key="news_universe_size"))
    delay = float(st.slider("Per-ticker delay (seconds)", min_value=0.0, max_value=1.0, value=0.05, step=0.01, key="news_delay"))
    source_mode = st.radio("Universe source", ["Auto-discover", "Manual list"], horizontal=True, key="news_universe_source")

    csv_path = _default_csv_path()
    st.caption(f"CSV path: `{csv_path}`")

    # Universe symbols
    symbols: List[str] = []
    if source_mode == "Auto-discover":
        try:
            symbols = list_universe(n=universe_size)
        except TypeError:
            symbols = list_universe(universe_size)
    else:
        raw = st.text_area("Manual symbols (comma/space separated)", key="news_manual_list")
        symbols = newswire_local.parse_ticker_text(raw)

    colA, colB, colC = st.columns([1,1,1])
    with colA:
        if st.button("Fetch & populate news CSV", use_container_width=True):
            df_new = _fetch_titles_for(symbols[:universe_size], per_symbol=10, delay_sec=delay)
            if not df_new.empty:
                if csv_path.exists():
                    df_old = newswire_local.load_news_csv(csv_path=csv_path)
                    df_all = pd.concat([df_old, df_new], ignore_index=True)
                else:
                    df_all = df_new
                newswire_local.save_news_csv(df_all, csv_path=csv_path)
                st.session_state["elite_news_df"] = df_all
                st.success(f"Collected {len(df_new)} items. CSV now has {len(df_all)} rows.")
            else:
                st.warning("No news items collected. Try a larger universe or increase per-symbol limit.")
    with colB:
        if csv_path.exists():
            bytes_ = csv_path.read_bytes()
            st.download_button("Download elite_news.csv", data=bytes_, file_name="elite_news.csv", mime="text/csv", use_container_width=True)
    with colC:
        if st.button("Run scanner on news tickers", use_container_width=True):
            df = newswire_local.load_news_csv(csv_path=csv_path) if csv_path.exists() else st.session_state.get("elite_news_df")
            recent = newswire_local.filter_recent(df, hours=12) if df is not None else pd.DataFrame()
            tickers = newswire_local.list_unique_tickers(recent)
            st.session_state["use_watchlist_universe"] = True
            st.session_state["watchlist_symbols"] = tickers
            st.success(f"Scanner will use {len(tickers)} news-derived tickers.")

    st.markdown("---")

    # Show recent news and derived tickers
    df_now = None
    if csv_path.exists():
        df_now = newswire_local.load_news_csv(csv_path=csv_path)
        st.session_state["elite_news_df"] = df_now
    else:
        df_now = st.session_state.get("elite_news_df")

    if df_now is None or df_now.empty:
        st.info("No news data found yet. Use **Fetch & populate news CSV** first.")
        return

    recent = newswire_local.filter_recent(df_now, hours=12)
    st.caption(f"Recent news in CSV (last 12h): {len(recent)}")
    with st.expander("Tickers derived from recent news (edit if needed)", expanded=True):
        tickers = newswire_local.list_unique_tickers(recent)
        txt = st.text_area("Ticker list", value="\n".join(tickers), height=160, key="news_ticker_list_text")
        st.caption(f"{len(tickers)} tickers after parsing.")
