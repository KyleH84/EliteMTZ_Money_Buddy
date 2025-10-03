from __future__ import annotations
import re
from pathlib import Path
import pandas as pd
import streamlit as st

# Try to import resolver for the Data directory if available
try:
    from BreakoutBuddy.program.modules.utilities.cloud_paths import resolve_data_dir  # type: ignore
except Exception:
    resolve_data_dir = None  # type: ignore

TICKER_RE = re.compile(r"\b[A-Z]{2,5}\b")

def _load_news_df() -> pd.DataFrame:
    # 1) If a dataframe was stored in session during fetch, prefer that
    df = st.session_state.get("elite_news_df")
    if isinstance(df, pd.DataFrame) and not df.empty:
        return df.copy()

    # 2) Try to read from Data/elite_news.csv
    try:
        app_root = Path(__file__).resolve().parents[3]  # .../BreakoutBuddy/program
        data_dir = None
        if resolve_data_dir is not None:
            data_dir = resolve_data_dir(app_root, "MONEY_BUDDY_DATA", "Data")
        else:
            data_dir = (app_root.parent / "Data")
        csv_path = data_dir / "elite_news.csv"
        if csv_path.exists():
            return pd.read_csv(csv_path)
    except Exception:
        pass
    return pd.DataFrame()

def _extract_tickers(df: pd.DataFrame) -> list[str]:
    if df is None or df.empty:
        return []
    # Combine text fields likely to carry tickers
    cols = [c for c in df.columns if str(c).lower() in ("title","summary","text","snippet","headline")]
    if not cols:
        cols = list(df.columns[:1])
    found: set[str] = set()
    for _, row in df[cols].fillna("").iterrows():
        blob = " ".join(str(row[c]) for c in cols)
        for m in TICKER_RE.findall(blob):
            if len(m) <= 5 and m.isupper():
                found.add(m)
    # Optionally filter by a universe present in session (if scanner pulled one)
    universe = st.session_state.get("latest_universe_symbols")
    if isinstance(universe, (list, set)) and universe:
        found = {t for t in found if t in set(universe)}
    return sorted(found)

def render_elitenewsbot_tab(*, settings=None):
    st.subheader("EliteNewsBot • Derived tickers from recent news")
    df = _load_news_df()
    if df.empty:
        st.info("No news data found yet. Use **Fetch & populate news CSV** first.")
        return

    # Recent items quick stats
    st.caption(f"{len(df)} news rows loaded.")
    with st.expander("Preview recent news (first 20 rows)", expanded=False):
        st.dataframe(df.head(20), use_container_width=True)

    tickers = _extract_tickers(df)
    st.markdown("### Tickers derived from recent news")
    st.text_area("Ticker list", value="\n".join(tickers), height=160, key="news_derived_tickers_text")
    st.caption(f"{len(tickers)} tickers after parsing.")

    # Stash for other tabs (e.g., Scanner)
    st.session_state["news_derived_tickers"] = tickers

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Copy to clipboard (client-side)", use_container_width=True):
            st.toast("Copy the text from the area above.", icon="✂️")
    with col2:
        if st.button("Run scanner on these tickers", use_container_width=True):
            st.session_state["use_watchlist_universe"] = True
            st.session_state["watchlist_symbols"] = tickers
            st.success("Scanner will use derived news tickers as its universe.")
