import streamlit as st
import pandas as pd

from utilities.health_widget import render_health_widget
from utilities.data_registry import load_active_snapshot, get_refresh_epoch
from utilities.feature_fixups import fill_feature_gaps, report_feature_gaps
from data.spy_loader import get_spy_prices

st.set_page_config(page_title="Reporting (Fixed)", layout="wide")
render_health_widget()

st.title("Reporting (Fixed)")

epoch = get_refresh_epoch()
try:
    df, path = load_active_snapshot(epoch)
except Exception as e:
    st.error(f"No data to report on: {type(e).__name__}: {e}")
    st.stop()

st.caption(f"Snapshot: {path}")

try:
    spy = get_spy_prices()  # yfinance real data, cached
except Exception as e:
    st.warning(f"SPY loader failed ({type(e).__name__}): {e}. RelSPY will remain empty.")
    spy = None

df = fill_feature_gaps(df, spy_ref=spy)
st.dataframe(df.head(50), use_container_width=True)

st.subheader("Feature gap audit")
st.dataframe(report_feature_gaps(df), use_container_width=True)
