from modules.utilities.reporting_fixed_panel import render_reporting_fixed_panel
# program/modules/tabs/about.py
from __future__ import annotations
from typing import Any
from pathlib import Path
import os
import streamlit as st

APP_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("BREAKOUTBUDDY_DATA", APP_ROOT / "Data")).expanduser().resolve()

def render_about_tab(*, settings: Any = None) -> None:
    st.header("About BreakoutBuddy")
    st.caption("Helper app for daily discovery, ranking, and quick analysis.")

    st.markdown("""
**BreakoutBuddy** streamlines your morning scan and intra-day checks. It pulls prices, computes lightweight features,
ranks candidates, and gives concise explanations you can actually act on.
""")

    st.markdown("### What each page does")

    with st.expander("Dashboard â€” Todayâ€™s Top Ranked", expanded=True):
        st.markdown("""
**Purpose:** See **todayâ€™s** ranked list at a glance, then drill down quickly.

**You can:**
- **Refresh now (internet)** to fetch current data via yfinance, compute features (`ChangePct`, `RVOL`, `RSI4`, `RelSPY`), and save `explore_snapshot_latest.csv` and `ranked_latest.csv` to `Data/`.
- **Load latest from disk** to reuse the most recent CSVs.
- Control **Top N** from the global Controls.
- Use **Quick Explain** to get a ruleâ€‘based "Why / Pros / Cons" for the selected ticker.

**When to use:** First stop of the day. Hit **Refresh now**, review the top slice, then open Quick Explain on a few names.
""")

    with st.expander("Explore â€” Build & Filter the Snapshot", expanded=False):
        st.markdown("""
**Purpose:** Build, filter, and export the **universe snapshot**.

**You can:**
- **Refresh from internet (yfinance)** or **Load latest from disk**.
- Choose **Universe** (use `Data\\universe.csv` if present, or toggle **Use watchlist** to restrict).
- Filter by **Min RVOL**, **Min ChangePct**, search by ticker, and sort by any column.
- **Download filtered CSV** of exactly what youâ€™re viewing.
- Use **Quick Explain** on the filtered set.

**When to use:** Curate and export a focused list for the day, or sanityâ€‘check what made it into Dashboard.
""")

    with st.expander("Watchlist â€” Maintain Your Symbols + Snapshot Explain", expanded=False):
        st.markdown("""
**Purpose:** Manage your personal list and see their latest snapshot with explanations.

**You can:**
- **Add/Remove tickers**; the list lives in `Data\\watchlist.csv`.
- See **enriched snapshot** for your list (and save `watchlist_snapshot_latest.csv` when applicable).
- Use **Quick Explain** perâ€‘ticker (same robust fallback logic used everywhere).

**When to use:** Keep recurring symbols in view; get a fast narrative on each.
""")

    with st.expander("Single â€” Oneâ€‘off Analyzer", expanded=False):
        st.markdown("""
**Purpose:** Type a symbol and get a oneâ€‘ticker deep dive from recent bars.

**You can:**
- Pull the last ~month (daily) via yfinance when needed.
- See OHLCV, autoâ€‘computed `ChangePct` and `RSI4` if missing.
- Use **Quick Explain** on the latest bar for that symbol.

**When to use:** Adâ€‘hoc checks from chat or an emailâ€”paste the ticker, analyze, move on.
""")

    with st.expander("Reports â€” Readyâ€‘made Views", expanded=False):
        st.markdown("""
**Purpose:** Quick canned views on the latest snapshot or ranks.

**Youâ€™ll get:**
- **Top Gainers / Top Losers** (by `ChangePct`)
- **High RVOL** (>= 1.5), sorted by intensity
- **Overbought / Oversold** using `RSI4` thresholds
- **Summary** stats (row count; averages/medians for key features)

**When to use:** Postâ€‘refresh pass to spot edges and extremes.
""")

    with st.expander("Agents â€” (Optional) learning weights", expanded=False):
        st.markdown("""
**Purpose:** Calibrate and apply agent weights (optional).

**You can:**
- **Calibrate agents (ridge)** on the latest ranked data.
- **Calibrate + Reâ€‘rank** to write a new `ranked_latest.csv` with the blend.
- View current weights and diagnostics.

**Notes:** The app is fully functional **without** agents. Quick Explain always falls back to a strong ruleâ€‘based analysis.
""")

    with st.expander("Admin â€” Storage, Diagnostics, and Utilities", expanded=False):
        st.markdown(f"""
**Purpose:** Configure storage and run maintenance.

**You can:**
- Set **Data folder** (current: `{DATA_DIR}`) and reset to default.
- Browse local CSVs; run **OHLCV maintenance** panel.
- **Agents & Rank:** view/calibrate weights; optional reâ€‘rank.
- **Local LLMs (GPT4All/.gguf):** point to a models folder, scan, and test.
- **Data QA:** open a CSV, autoâ€‘analyze columns and distributions, and (if available) ask a local model to summarize.
- **Maintenance:** clean `__pycache__`/build junk.
- **Market Regime:** show current highâ€‘level flags if configured.
- **Utilities:** quick universe scan, health checks, and data diagnostics.
""")

    st.markdown("---")
    st.markdown("### How things work (expandable)")

    with st.expander("Data model & files", expanded=False):
        st.markdown("""
- Default data directory: `Data/` under the app root (override via **Admin â–¸ Data folder** or `BREAKOUTBUDDY_DATA` env var).
- Key CSVs the app reads/writes:
  - `explore_snapshot_latest.csv` â€” latest universe snapshot from Explore/Dashboard refresh.
  - `ranked_latest.csv` â€” ranked view written after refresh or reâ€‘rank.
  - `watchlist.csv` â€” your saved symbols.
  - `watchlist_snapshot_latest.csv` â€” snapshot filtered to your watchlist.
- Nothing should be created **above** the app rootâ€”paths are rooted in `Data/` by design.
""")

    with st.expander("Feature engineering", expanded=False):
        st.markdown("""
- **ChangePct:** dayâ€‘overâ€‘day close percent change.
- **RVOL:** today's volume / 20â€‘day average volume.
- **RSI4:** 4â€‘period RSI on close.
- **RelSPY:** today's `ChangePct` minus SPY's `ChangePct` (pulled alongside).
- Optional columns supported if present: `P_up`, `ConnorsRSI`, `SqueezeHint`, `Combined`, `AgentBoost_exact`, `Combined_with_agents`.
""")

    with st.expander("Ranking logic", expanded=False):
        st.markdown("""
- Default ranking (agentâ€‘free): `z(ChangePct) + z(RVOL) + z(RelSPY)`.
- When agent weights are available, Admin/Agents can write a blended rank to `ranked_latest.csv`.
- Explore & Dashboard always display your chosen **Top N** with these columns prioritized:
  `Ticker, Open, High, Low, Close, Volume, ChangePct, P_up, RelSPY, RVOL, RSI4, ConnorsRSI, SqueezeHint, Combined, AgentBoost_exact, Combined_with_agents`.
""")

    with st.expander("Quick Explain (ruleâ€‘based)", expanded=False):
        st.markdown("""
- Works **without** agents. For the selected ticker it evaluates:
  `RVOL`, `P_up`, `RelSPY`, `ChangePct`, `RSI4`, `ConnorsRSI`, `SqueezeHint`, `Combined`, `Combined_with_agents` (when present).
- Produces:
  - A **label** (Bullish / Leaning Bullish / Neutral / Leaning Bearish / Bearish)
  - A concise **Why** sentence with actual numbers (and a caution if stretched/weak)
  - **Pros / Cons** bullets listing each factor and rationale
  - A small **Detailed analysis** table showing component points and reasons
- It never prints raw `None` or garbage values; everything is formatted for humans.
""")

    with st.expander("Live data & performance notes", expanded=False):
        st.markdown("""
- **yfinance** powers the live refresh. If itâ€™s missing in the venv, the UI will tell you.
- **DuckDB** is supported; if the native module can't load, the app gracefully falls back to CSV workflows.
- Streamlit caching is used where helpful; unique widget keys prevent duplicate-ID errors.
- Large universes fetch in a loop; use the **Universe size** control to cap if needed.
""")

    st.markdown("---")
    st.markdown("If you want this About page to include a **changelog** or **keyboard shortcuts**, say the word and I'll add it without touching other pages.")


# Auto-wired panel
render_reporting_fixed_panel()

