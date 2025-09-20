# --- Patch module: Maintenance with Calibrate, Scan, Health, and stale note ---
def _section_maintenance():
    import streamlit as st
    st.subheader("Maintenance")
    st.caption("If pages feel stale, Admin → Calibrate + Re-rank now.")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Calibrate + Re-rank now"):
            try:
                from modules.services import scoring as _sc
                _ = _sc.rank_now({"universe_size": 300, "top_n": 50})
                st.success("Re-ranking complete.")
            except Exception as e:
                st.error(f"Calibration failed: {e}")
    with c2:
        if st.button("Scan universe now"):
            try:
                from modules.engines.runner import quick_scan as _scan
                n = _scan(limit=500)
                st.success(f"Scan complete: {n} rows.")
            except Exception as e:
                st.error(f"Scan failed: {e}")
    with c3:
        if st.button("Health check"):
            try:
                from modules.health import run_health_check as _hc
                rep = _hc()
                st.json(rep)
                st.success("Health OK." if rep.get("ok") else "Health reported issues above.")
            except Exception as e:
                st.error(f"Health check failed: {e}")
