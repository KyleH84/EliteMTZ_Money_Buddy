from __future__ import annotations
from dataclasses import dataclass
import streamlit as st
from modules.glossary import render_sidebar_help

@dataclass
class SidebarSettings:
    universe_size: int
    top_n: int
    sort_by: str
    agent_weight: float
    friendly: bool
    auto_scan: bool
    typed_symbol: str

def render_sidebar(*, default_universe: int = 300, default_topn: int = 25, default_agent_weight: float = 0.30, has_agents: bool = False) -> SidebarSettings:
    st.sidebar.header("Controls")
    universe_size = int(st.sidebar.slider("Universe size", 20, 2000, int(default_universe), 10))
    top_n = int(st.sidebar.slider("Top N", 5, 200, int(default_topn), 5))
    sort_choices = [
        "Combined","P_up","Relative Strength","RVOL","RSI4 (low→high)",
        "Change %","ConnorsRSI (low→high)","SqueezeHint","SqueezeOn","ADX","ATR","Gap %"
    ]
    sort_by = st.sidebar.selectbox("Sort by", sort_choices, index=0)
    agent_weight = float(st.sidebar.slider("Agent blend weight", 0.0, 1.0, float(default_agent_weight), 0.05)) if has_agents else 0.0
    friendly = st.sidebar.toggle("Plain-English Why", value=True)
    auto_scan = st.sidebar.toggle("Auto-scan", value=True)
    typed_symbol = ""
    st.session_state["bb_analyze_ticker"] = typed_symbol
    render_sidebar_help(st)
     # moved to Admin page: manual scan button removed   # state flag only
    return SidebarSettings(
        universe_size=universe_size,
        top_n=top_n,
        sort_by=sort_by,
        agent_weight=agent_weight,
        friendly=friendly,
        auto_scan=auto_scan,
        typed_symbol=typed_symbol,
    )
