# modules/utilities/reporting_fixed_panel.py
import streamlit as st

# Strict local imports (inside BreakoutBuddy/program)
from utilities.data_registry import load_active_snapshot, get_refresh_epoch
from utilities.feature_fixups import fill_feature_gaps, report_feature_gaps
from data.spy_loader import get_spy_prices

def render_reporting_fixed_panel():
    st.subheader("Reporting — Fixed")
    st.caption("Loads the latest snapshot from Data/, fetches real SPY for RelSPY, and fills indicators.")

    epoch = get_refresh_epoch()
    try:
        df, path = load_active_snapshot(epoch)
    except Exception as e:
        st.error(f"No data to report on: {type(e).__name__}: {e}")
        return

    st.text(f"Snapshot: {path}")

    try:
        spy = get_spy_prices()
    except Exception as e:
        st.warning(f"SPY loader failed ({type(e).__name__}): {e}. RelSPY will remain empty.")
        spy = None

    df = fill_feature_gaps(df, spy_ref=spy)
    st.dataframe(df.head(50), use_container_width=True)

    with st.expander("Feature gap audit"):
        st.dataframe(report_feature_gaps(df), use_container_width=True)