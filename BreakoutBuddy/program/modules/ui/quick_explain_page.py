# program/modules/ui/quick_explain_page.py
from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple
import math
import pandas as pd  # type: ignore
import streamlit as st

# ------------------------- utils -------------------------
def _fmt(v: Any) -> str:
    try:
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            return "-"
        if abs(fv) >= 1000000:
            return f"{fv:,.0f}"
        if abs(fv) >= 1000:
            return f"{fv:,.0f}"
        if abs(fv) >= 10:
            return f"{fv:,.2f}"
        return f"{fv:.3f}"
    except Exception:
        return str(v)

def _lower_map(cols: List[str]) -> Dict[str, str]:
    return {c.lower(): c for c in cols}

def _get(row: pd.Series, name: str, default=None):
    lm = _lower_map(list(row.index))
    col = lm.get(name.lower())
    return row[col] if col in row else default

def _has(row: pd.Series, name: str) -> bool:
    return any(c.lower() == name.lower() for c in row.index)

def _truthy(v: Any) -> bool:
    if v is None: return False
    if isinstance(v, (int, float)): return v != 0
    s = str(v).strip().lower()
    return s in ("true","1","on","yes","y","t")

# --------------------- rule-based engine ---------------------
def _score_components(row: pd.Series) -> List[Tuple[str, float, str]]:
    """Return list of (name, points, rationale) for rule components."""
    comps: List[Tuple[str, float, str]] = []

    def add(name: str, pts: float, why: str):
        comps.append((name, float(pts), why))

    # RVOL
    rvol = _get(row, "RVOL")
    if rvol is not None:
        rv = float(rvol)
        if rv >= 1.8: add("RVOL", 2.5, f"very elevated volume ({_fmt(rv)})")
        elif rv >= 1.5: add("RVOL", 2.0, f"high volume ({_fmt(rv)})")
        elif rv >= 1.1: add("RVOL", 1.0, f"supportive volume ({_fmt(rv)})")
        elif rv < 0.9: add("RVOL", -1.0, f"subpar volume ({_fmt(rv)})")

    # P_up
    p_up = _get(row, "P_up")
    if p_up is not None:
        pu = float(p_up)
        if pu >= 0.65: add("P_up", 2.0, f"high win-prob ({_fmt(pu)})")
        elif pu >= 0.58: add("P_up", 1.5, f"good win-prob ({_fmt(pu)})")
        elif pu >= 0.55: add("P_up", 1.0, f"mild edge ({_fmt(pu)})")
        elif pu <= 0.45: add("P_up", -1.0, f"low win-prob ({_fmt(pu)})")

    # RelSPY
    rel = _get(row, "RelSPY")
    if rel is not None:
        rv = float(rel)
        if rv > 1.0: add("RelSPY", 2.0, f"strongly beating SPY ({_fmt(rv)})")
        elif rv > 0.4: add("RelSPY", 1.0, f"beating SPY ({_fmt(rv)})")
        elif rv < 0: add("RelSPY", -1.0, f"lagging SPY ({_fmt(rv)})")

    # ChangePct
    ch = _get(row, "ChangePct")
    if ch is not None:
        cp = float(ch)
        if cp >= 2.0: add("ChangePct", 2.0, f"strong day move (+{_fmt(cp)}%)")
        elif cp >= 0.5: add("ChangePct", 1.0, f"positive day move (+{_fmt(cp)}%)")
        elif cp <= -1.0: add("ChangePct", -2.0, f"weak day move ({_fmt(cp)}%)")
        elif cp < 0: add("ChangePct", -1.0, f"negative day move ({_fmt(cp)}%)")

    # RSI4
    rsi4 = _get(row, "RSI4")
    if rsi4 is not None:
        r = float(rsi4)
        if 55 <= r <= 70: add("RSI4", 1.0, f"momentum improving (RSI4 {_fmt(r)})")
        elif r > 85: add("RSI4", -1.5, f"overheated (RSI4 {_fmt(r)})")
        elif r < 30: add("RSI4", -1.0, f"weak momentum (RSI4 {_fmt(r)})")

    # ConnorsRSI
    cr = _get(row, "ConnorsRSI")
    if cr is not None:
        c = float(cr)
        if 60 <= c <= 80: add("ConnorsRSI", 0.5, f"healthy (CRSI {_fmt(c)})")
        elif c > 90: add("ConnorsRSI", -1.0, f"stretched (CRSI {_fmt(c)})")
        elif c < 20: add("ConnorsRSI", -0.5, f"weak (CRSI {_fmt(c)})")

    # SqueezeHint
    sq = _get(row, "SqueezeHint")
    if sq is not None and _truthy(sq):
        add("SqueezeHint", 0.5, "in squeeze; potential energy build")

    # Combined (base model)
    cmb = _get(row, "Combined")
    if cmb is not None:
        v = float(cmb)
        if v > 0: add("Combined", 0.5, f"base score positive ({_fmt(v)})")
        elif v < 0: add("Combined", -0.5, f"base score negative ({_fmt(v)})")

    # Combined_with_agents (if present, small nudge even if agents disabled)
    cwa = _get(row, "Combined_with_agents")
    if cwa is not None:
        v = float(cwa)
        if v > 0: add("Combined_with_agents", 0.5, f"blended score positive ({_fmt(v)})")
        elif v < 0: add("Combined_with_agents", -0.5, f"blended score negative ({_fmt(v)})")

    return comps

def _summarize_why(row: pd.Series, comps: List[Tuple[str,float,str]]) -> str:
    # Build a short line using the most impactful positive items, include a caution if overheated/weak
    pros = sorted([c for c in comps if c[1] > 0], key=lambda x: x[1], reverse=True)
    cons = sorted([c for c in comps if c[1] < 0], key=lambda x: x[1])

    parts: List[str] = []
    # Prefer RVOL/RelSPY/P_up/ChangePct in the sentence
    for key in ("RVOL","RelSPY","P_up","ChangePct"):
        for name, pts, why in pros:
            if name == key:
                parts.append(why); break
    if not parts and pros:
        parts.append(pros[0][2])

    # Add a caution if present
    overheated = [c for c in cons if ("overheated" in c[2] or "negative" in c[2] or "weak" in c[2])]
    if overheated:
        parts.append(f"but caution: {overheated[0][2]}")

    return (parts and (parts[0][0].upper() + parts[0][1:])) if parts else "Mixed signals today."

def _pros_cons_from_comps(comps: List[Tuple[str,float,str]]) -> Tuple[List[str], List[str]]:
    pros = [f"{n}: {w}" for n,pts,w in comps if pts > 0]
    cons = [f"{n}: {w}" for n,pts,w in comps if pts < 0]
    return pros, cons

def _score_total(comps: List[Tuple[str,float,str]]) -> float:
    return round(sum(pts for _,pts,_ in comps), 2)

def _label_from_score(s: float) -> str:
    if s >= 4: return "Bullish"
    if s >= 2: return "Leaning Bullish"
    if s <= -3: return "Bearish"
    if s <= -1: return "Leaning Bearish"
    return "Neutral"

# ------------------------- UI -------------------------
def render(*, df: pd.DataFrame, default_ticker: Optional[str] = None, show_header: bool = True, key_prefix: str = 'qe'):
    if show_header:
        st.markdown("### Quick explain")

    if df is None or df.empty:
        st.info("No data to explain.")
        return

    # Ticker select
    tickers = df["Ticker"].astype(str).tolist() if "Ticker" in df.columns else [str(x) for x in df.index]
    if not tickers:
        st.info("No tickers available."); return

    default = default_ticker or tickers[0]
    idx = tickers.index(default) if default in tickers else 0
    chooser = st.selectbox("Pick a ticker", tickers, index=idx, key=f"{key_prefix}_quick_explain_ticker")

    # Row
    sel = df[df["Ticker"].astype(str) == chooser] if "Ticker" in df.columns else df.loc[[chooser]]
    if sel is None or len(sel) == 0:
        st.info("No row found for that ticker."); return
    row = sel.iloc[0]

    # Compute components and score
    comps = _score_components(row)
    total = _score_total(comps)
    label = _label_from_score(total)

    # Why
    st.markdown("### Why")
    st.markdown(f"- {label}: {_summarize_why(row, comps)}")

    # Detailed analysis
    with st.expander("Detailed analysis", expanded=False):
        # Show a small table with component scores and rationales
        if comps:
            table = pd.DataFrame([{"Factor": n, "Points": pts, "Reason": why} for (n,pts,why) in comps])
            # Show most important first
            table = table.sort_values(by="Points", ascending=False).reset_index(drop=True)
            st.dataframe(table, use_container_width=True, hide_index=True)
        else:
            st.write("No signals available for this row.")

    # Pros / Cons
    p_list, c_list = _pros_cons_from_comps(comps)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Pros")
        if p_list:
            for line in p_list:
                st.write(f"- {line}")
        else:
            st.write("- None")
    with col2:
        st.markdown("### Cons")
        if c_list:
            for line in c_list:
                st.write(f"- {line}")
        else:
            st.write("- None")
