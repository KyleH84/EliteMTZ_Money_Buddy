
from __future__ import annotations
from pathlib import Path
import runpy
import sys
import streamlit as st

st.set_page_config(page_title="Money Buddy — Cloud", page_icon="💼", layout="wide")

ROOT = Path(__file__).resolve().parent
APPS = {
    "AstroLotto": ROOT / "AstroLotto" / "programs" / "app_main.py",
    "BreakoutBuddy": ROOT / "BreakoutBuddy" / "program" / "00_Dashboard.py",
}

st.title("💼 Money Buddy — Cloud")
st.caption("Single-entry app that routes to AstroLotto or BreakoutBuddy in the same Streamlit process (cloud-safe).")

with st.sidebar:
    st.header("Choose an app")
    choice = st.radio("App", list(APPS.keys()), index=0)

missing = [name for name, path in APPS.items() if not path.exists()]
if missing:
    st.error("Missing entry files for: " + ", ".join(missing))
    with st.expander("Debug info"):
        for name, p in APPS.items():
            st.write(f"{name}: {p}")
    st.stop()

with st.expander("Environment / Secrets (diagnostic)"):
    bridge = st.secrets.get("LLMBRIDGE_URL", None) if hasattr(st, "secrets") else None
    st.write({"LLMBRIDGE_URL": bool(bridge)})

st.divider()
st.subheader(f"▶ {choice}")
st.caption("Running inline. If you navigate back here, use the sidebar to switch apps.")

script_path = APPS[choice]
module_dir = str(script_path.parent)

# Prepend the target module directory so 'from X import Y' works for sibling modules.
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

try:
    runpy.run_path(str(script_path), run_name="__main__")
except SystemExit:
    pass
except Exception as e:
    st.exception(e)
