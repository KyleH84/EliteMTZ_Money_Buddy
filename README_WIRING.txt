WIRING FIX PACK (Real data + Watchlist + Health)
===============================================

This pack gives you:
  1) A sidebar **Cache & Storage Health** widget.
  2) Real **SPY** data loader via yfinance for RelSPY (cached).
  3) A **data registry** that finds the latest snapshot/export under Data/ so Reporting stops saying "No data".
  4) A robust **watchlist** module with read/write/add/remove using DuckDB or CSV fallback.
  5) Feature backfills for RSI4 / ConnorsRSI / RVOL / RelSPY / SqueezeHint / (optional) P_up baseline.

Files:
  utilities/caching.py
  utilities/health_widget.py
  utilities/feature_fixups.py
  utilities/data_registry.py
  data/spy_loader.py
  modules/watchlist.py

---- QUICK HOOKUP ----

A) Sidebar health
   in your main app file:
     from utilities.health_widget import render_health_widget
     render_health_widget()

B) Dashboard/Explore (after you refresh snapshot)
   When your refresh completes, bump the shared epoch so readers reload:
     from utilities.data_registry import bump_refresh_epoch
     bump_refresh_epoch()

C) Reporting page (replace your current "load snapshot" logic)
   Use the registry + fixups so you get real values, not None:
     import streamlit as st
     from utilities.data_registry import load_active_snapshot, get_refresh_epoch
     from utilities.feature_fixups import fill_feature_gaps, report_feature_gaps
     from data.spy_loader import get_spy_prices

     epoch = get_refresh_epoch()
     df, path = load_active_snapshot(epoch)   # auto-cached, invalidates after refresh
     spy = get_spy_prices()                   # cached fetch
     df = fill_feature_gaps(df, spy_ref=spy)  # fills missing indicators

     st.caption(f"Snapshot: {path}")
     st.dataframe(df.head(25), use_container_width=True)
     st.dataframe(report_feature_gaps(df))

D) Watchlist
   Replace broken calls with the provided module:
     from modules.watchlist import read_watchlist, add_to_watchlist, remove_from_watchlist, write_watchlist

   Example usage:
     cur = read_watchlist()
     add_to_watchlist("AAPL")
     remove_from_watchlist("TSLA")
     write_watchlist(cur + ["MSFT"])

   Storage:
     - Prefers DuckDB at Data/watchlist.duckdb (table: watchlist).
     - Falls back to Data/watchlist.csv if duckdb isn't available.

Notes:
  - The registry looks for files under Data/ matching *candidates*.* or *snapshot*.* (csv/parquet/feather).
  - If your actual filenames differ, set SNAP_PATTERNS at the top of utilities/data_registry.py.
  - All caching uses Streamlit's cache with safe defaults. No fake data; SPY is fetched with yfinance.