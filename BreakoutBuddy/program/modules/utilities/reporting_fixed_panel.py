# modules/utilities/reporting_fixed_panel.py
import streamlit as st

# Strict local imports (inside BreakoutBuddy/program)
from utilities.data_registry import load_active_snapshot, get_refresh_epoch
try:
    from utilities.feature_fixups import fill_feature_gaps, report_feature_gaps  # root shim if available
except Exception:
    try:
        # Fallback to BB local utilities; alias ensure_basic_indicators
        from BreakoutBuddy.program.utilities.feature_fixups import ensure_basic_indicators as fill_feature_gaps  # type: ignore
        def report_feature_gaps(df):
            try:
                missing = []
                for c in ["P_up","ConnorsRSI","SqueezeHint","AgentBoost_exact"]:
                    if c not in df.columns or df[c].isna().all():
                        missing.append(c)
                return {"missing": missing, "rows": len(df)}
            except Exception:
                return {"missing": [], "rows": 0}
    except Exception:
        def fill_feature_gaps(df, spy_ref=None):
            return df
        def report_feature_gaps(df):
            return {"missing": [], "rows": getattr(df, 'shape', [0,0])[0] if hasattr(df,'shape') else 0}
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