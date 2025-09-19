
# page_report_bb.py
import streamlit as st
import pandas as pd
import numpy as np
import io, os, json, time

st.set_page_config(page_title="BreakoutBuddy: Report", layout="wide")
st.title("BreakoutBuddy ▸ Report")
st.caption("Build a quick, shareable snapshot report. Point to a snapshot CSV (or paste a table).")

snap_csv = st.text_input("Snapshot CSV (exported ranked table)", value="Data/bb_snapshot.csv")
top_n = st.number_input("Top N", value=20, min_value=5, max_value=200, step=5)
include_watchlist = st.checkbox("Include watchlist evaluation", value=True)
wl_csv = "Data/watchlist.csv"

def load_df(path):
    if not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None

df = load_df(snap_csv)
if df is None:
    st.warning("No snapshot found. Export a ranked table to CSV from the dashboard and point to it here (e.g., Data/bb_snapshot.csv).")
    st.stop()

# Basic normalization
if "Ticker" not in df.columns and "ticker" in df.columns:
    df.rename(columns={"ticker":"Ticker"}, inplace=True)
if "Combined" not in df.columns and "FinalScore" in df.columns:
    df["Combined"] = df["FinalScore"]

# Slice top
top = df.sort_values("Combined", ascending=False).head(int(top_n)).copy()
cols = [c for c in ["Ticker","Combined","HeuristicScore","RelSPY","RVOL","RSI4","ConnorsRSI","SqueezeHint","ChangePct","Why"] if c in top.columns]

st.subheader("Top list preview")
st.dataframe(top[cols], width="stretch", height=360)

# Regime (if present)
regime_fields = [c for c in ["spy20d_trend","spy20d_vol","ma200_slope5","vix_percentile"] if c in df.columns]
regime_line = ", ".join([f"{c}={df[c].iloc[0]}" for c in regime_fields]) if regime_fields else "n/a"

# Watchlist evaluation
wl = None
if include_watchlist and os.path.exists(wl_csv):
    try:
        wl = pd.read_csv(wl_csv)
        wl_tickers = wl["Ticker"].astype(str).tolist()
        miss = [t for t in wl_tickers if t not in df["Ticker"].astype(str).tolist()]
        have = [t for t in wl_tickers if t in df["Ticker"].astype(str).tolist()]
        st.subheader("Watchlist coverage")
        st.write(f"Tickers in snapshot: {len(have)} / {len(wl_tickers)}")
        if have:
            st.dataframe(df[df["Ticker"].astype(str).isin(have)][cols], width="stretch", height=200)
        if miss:
            st.caption("Missing from snapshot: " + ", ".join(miss))
    except Exception:
        st.warning("Could not read watchlist.csv; skipping.")

# Build markdown report
def build_md():
    lines = []
    lines += ["# BreakoutBuddy — Snapshot Report", ""]
    lines += [f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    lines += [f"Universe size: {len(df)}"]
    lines += [f"Regime: {regime_line}", ""]
    lines += ["## Top list", ""]
    lines += [top[cols].to_markdown(index=False)]
    if include_watchlist and wl is not None:
        lines += ["", "## Watchlist in snapshot", ""]
        if have:
            lines += [df[df["Ticker"].astype(str).isin(have)][cols].to_markdown(index=False)]
        else:
            lines += ["(No watchlist tickers present.)"]
    return "\n".join(lines)

md = build_md()
st.subheader("Report (Markdown)")
st.code(md, language="markdown")

# Download as file
b = md.encode("utf-8")
st.download_button("Download report.md", b, file_name="bb_report.md", mime="text/markdown")
