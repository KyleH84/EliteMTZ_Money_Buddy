from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# program/modules/tabs/dashboard.py

from typing import Any, Callable, Optional, Tuple
import pandas as pd
import streamlit as st

# Types for the hooks we expect (duck-typed; no hard dependency)
RankNowFn = Callable[..., Tuple[pd.DataFrame, dict, pd.DataFrame, Any, Any]]
FriendlyLinesFn = Callable[[pd.Series], list[str]]
AnalyzeOneFn = Callable[..., pd.DataFrame]
ComputeRegimeFn = Callable[[], dict]

def _safe_getattr(obj: Any, name: str, default: Any = None):
    try:
        return getattr(obj, name, default)
    except Exception:
        return default

def _safe_friendly_lines(fn: Optional[FriendlyLinesFn], row: pd.Series) -> list[str]:
    if fn is None:
        return []
    try:
        return fn(row)
    except Exception:
        return []

def _simple_pros_cons(row: pd.Series) -> tuple[list[str], list[str]]:
    """
    Lightweight Pros/Cons synthesis if a dedicated analyzer isn't available.

    Pros  -> select a few highest positive numeric fields (signals)
    Cons  -> select a few lowest/negative numeric fields
    """
    pros, cons = [], []
    try:
        # pick up to 4 numeric columns besides 'Ticker'
        numerics = row.drop(labels=[c for c in ["Ticker", "ticker"] if c in row.index], errors="ignore")
        numerics = numerics.dropna()
        if isinstance(numerics, pd.Series):
            # Keep only numeric-like
            numerics = numerics[[k for k, v in numerics.items() if isinstance(v, (int, float))]]

        if len(numerics) > 0:
            top_pos = sorted(numerics.items(), key=lambda kv: kv[1], reverse=True)[:4]
            top_neg = sorted(numerics.items(), key=lambda kv: kv[1])[:4]

            for k, v in top_pos:
                pros.append(f"{k}: {v:.3f}")
            for k, v in top_neg:
                cons.append(f"{k}: {v:.3f}")
    except Exception:
        pass
    return pros, cons

def _analyze_one_safe(fn: Optional[AnalyzeOneFn], ticker: str) -> pd.DataFrame:
    if fn is None or not ticker:
        return pd.DataFrame()
    try:
        return fn(ticker=ticker)
    except TypeError:
        # Support older signature analyze_one_fn(ticker)
        try:
            return fn(ticker)
        except Exception:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def _render_regime(regime: Optional[dict]):
    if not isinstance(regime, dict) or not regime:
        return
    cols = st.columns(min(4, max(1, len(regime))))
    i = 0
    for k, v in regime.items():
        with cols[i % len(cols)]:
            st.metric(k, value=str(v))
        i += 1

def render_dashboard_tab(
    *,
    settings: Any,
    rank_now_fn: Optional[RankNowFn] = None,
    friendly_lines_fn: Optional[FriendlyLinesFn] = None,
    analyze_one_fn: Optional[AnalyzeOneFn] = None,
    compute_regime_fn: Optional[ComputeRegimeFn] = None,
    has_agents: bool = False,
) -> None:
    """
    Main dashboard:
      - Top ranked table
      - Quick explain (dropdown) with Why + Pros/Cons
      - Optional regime summary
    """

    st.subheader("BreakoutBuddy ▸ Dashboard")
    st.caption("Ranked snapshot, quick analyze, simple explain. Clean dropdown instead of the giant button wall.")

    # Pull settings with safe defaults
    universe_size = _safe_getattr(settings, "universe_size", 300)
    top_n         = _safe_getattr(settings, "top_n", 25)
    sort_by       = _safe_getattr(settings, "sort_by", None)
    agent_weight  = _safe_getattr(settings, "agent_weight", 0.30)

    # Compute regime (optional and fast)
    regime = None
    try:
        if compute_regime_fn:
            regime = compute_regime_fn()
    except Exception:
        regime = None

    if isinstance(regime, dict) and regime:
        with st.expander("Market Regime", expanded=False):
            _render_regime(regime)

    # Rank now (core data)
    ranked = pd.DataFrame()
    try:
        if rank_now_fn:
            _, _, ranked, auc, _ = rank_now_fn(
                universe_size=universe_size,
                top_n=top_n,
                sort_by=sort_by,
                agent_weight=agent_weight,
                settings=settings,
            )
    except Exception as e:
        st.error(f"Ranking failed: {e}")

    # Layout: table on the left, explain on the right
    left, right = st.columns([3, 2])

    with left:
        st.markdown("### Top ranked")
        if ranked is None or ranked.empty:
            st.info("No ranked results to show.")
        else:
            # Prefer a 'Ticker' column to be first if present
            cols = list(ranked.columns)
            if "Ticker" in cols:
                cols = ["Ticker"] + [c for c in cols if c != "Ticker"]
            st.dataframe(
                ranked[cols],
                use_container_width=True,
                hide_index=True,
            )

    with right:
        st.markdown("### Quick explain")
        tickers = []
        if ranked is not None and not ranked.empty:
            colname = "Ticker" if "Ticker" in ranked.columns else ("ticker" if "ticker" in ranked.columns else None)
            if colname:
                tickers = ranked[colname].astype(str).tolist()

        if not tickers:
            st.caption("Rank something first to enable quick explain.")
            return

        sel = st.selectbox("Pick a ticker", tickers, index=0, key="bb_quick_explain_dropdown")

        # Fetch the selected row
        row = None
        try:
            colname = "Ticker" if "Ticker" in ranked.columns else ("ticker" if "ticker" in ranked.columns else None)
            if colname:
                row = ranked.loc[ranked[colname].astype(str) == str(sel)].iloc[0]
        except Exception:
            row = None

        if row is None:
            st.warning("Selection not found in ranked results.")
            return

        # WHY (friendly lines)
        lines = _safe_friendly_lines(friendly_lines_fn, row)
        if lines:
            st.write("**Why**")
            for ln in lines:
                st.markdown(f"- {ln}")

        # ANALYZE (optional deeper view)
        with st.expander("Detailed analysis", expanded=False):
            detail = _analyze_one_safe(analyze_one_fn, str(sel))
            if detail is not None and not detail.empty:
                st.dataframe(detail, use_container_width=True, hide_index=True)
            else:
                st.caption("No detailed analysis available.")

        # PROS / CONS (simple synthesis if needed)
        pros, cons = _simple_pros_cons(row)
        if pros or cons:
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Pros**")
                for p in pros[:5]:
                    st.markdown(f"- {p}")
            with c2:
                st.write("**Cons**")
                for c in cons[:5]:
                    st.markdown(f"- {c}")

    # Optional footer
    st.caption("Tip: adjust Top N / Universe in the sidebar to update the dropdown and table.")
