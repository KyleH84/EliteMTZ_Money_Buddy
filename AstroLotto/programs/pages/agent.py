from __future__ import annotations

from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

"""
Agents page for AstroLotto.

This module defines a Streamlit page function `render()` so the main app can
call it from a tab. It also auto-renders when executed by Streamlit as a page.

Safe to import: no Streamlit calls at import time.
"""
import importlib
from pathlib import Path
import streamlit as st


def _load_agent_response():
    """Return (callable, module_name) for agent_response, or (None, None)."""
    candidates = [
        "programs.agent.langchain_lottery_agent",  # your backend
        "programs.agent.main",                     # alt layout
        "programs.agent.page",                     # alt layout
        "agent",                                   # last-resort top-level
    ]
    last_err = None
    for modname in candidates:
        try:
            mod = importlib.import_module(modname)
            fn = getattr(mod, "agent_response", None)
            if callable(fn):
                return fn, modname
        except Exception as e:
            if last_err is None:
                last_err = (modname, e)
            continue
    # surface first error inline when page runs
    return None, last_err


def render():
    st.title("🤖 AI Agent (Lottery Analysis)")
    st.caption("Ask things like: 'most frequent numbers', 'pattern summary', 'build a model', 'show frequency chart'.")

    # Resolve app root and default CSV (if present)
    APP_ROOT = Path(__file__).resolve().parents[2]  # .../AstroLotto
    default_csv = APP_ROOT / "Data" / "cached_powerball_data.csv"
    csv_default_str = str(default_csv) if default_csv.exists() else ""

    st.write("### Data source")
    csv_path = st.text_input(
        "Dataset CSV path",
        csv_default_str,
        help="Path to a CSV. Leave blank to let the agent use its own defaults.",
    )
    uploaded = st.file_uploader("...or upload a CSV file", type=["csv"])

    tmp_path: Path | None = None
    if uploaded is not None:
        tmp_dir = APP_ROOT / "TempUploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / "agent_upload.csv"
        with open(tmp_path, "wb") as f:
            f.write(uploaded.read())

    st.write("### Question")
    prompt = st.text_input("Your question", "What are the most frequent numbers?")

    run = st.button("Run", type="primary")

    if run:
        agent_response, err = _load_agent_response()
        if agent_response is None:
            if err:
                modname, exc = err
                st.error(f"Failed to import `{modname}`: {exc}")
            else:
                st.error(
                    "Agents backend not found. Expected `agent_response` in one of: "
                    "`programs.agent.langchain_lottery_agent`, `programs.agent.main`, "
                    "`programs.agent.page`, or `agent`."
                )
            st.stop()

        try:
            # Prefer uploaded CSV; else use text path if provided; else None
            df_or_path = str(tmp_path) if tmp_path else (csv_path or None)
            result = agent_response(prompt, df_or_path=df_or_path)

            rtype = (result or {}).get("type") if isinstance(result, dict) else None
            if rtype == "plotly" and isinstance(result.get("figure"), object):
                st.plotly_chart(result["figure"], width="stretch")
            elif rtype in ("matplotlib", "mpl") and result.get("figure") is not None:
                import matplotlib.pyplot as plt  # lazy
                st.pyplot(result["figure"])
            elif rtype in ("dataframe", "table") and result.get("data") is not None:
                import pandas as pd  # lazy
                st.dataframe(result["data"], width="stretch")
            elif rtype == "json":
                st.json(result.get("data"))
            else:
                text = result.get("text") if isinstance(result, dict) else str(result)
                st.write(text or "(no result)")

            with st.expander("Details", expanded=False):
                st.caption(f"Backend module: `{getattr(agent_response, '__module__', 'unknown')}`")
                if tmp_path:
                    st.caption(f"Uploaded CSV saved to: `{tmp_path}`")
        except Exception as e:
            st.exception(e)


# Auto-render when executed by Streamlit as a page (no recursive bootstrap)
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore
    if get_script_run_ctx() is not None:
        render()
except Exception:
    # Fallback: if we're under 'streamlit run', just call render()
    render()
