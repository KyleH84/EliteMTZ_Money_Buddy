# Admin page (v14.6+ UI upgrade)
import streamlit as st
from pathlib import Path

# --- minimal bootstrap so "programs" package is importable regardless of CWD ---
import sys as _sys
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
# ------------------------------------------------------------------------------

st.set_page_config(page_title="Admin", layout="wide")
st.title("Admin")

root = Path(__file__).resolve().parents[2]

tab1, tab2, tab3, tab4 = st.tabs(["Data & Health", "Analytics", "Models", "Tools"])

with tab1:
    st.subheader("Cache Status & Repair")
    from programs.features.health import GAME_TO_CACHE, check_one, delete_if_empty
    cols = st.columns(3)
    for i, game in enumerate(GAME_TO_CACHE.keys()):
        if i % 3 == 0: cols = st.columns(3)
        with cols[i % 3]:
            ch = check_one(root, game)
            st.write(f"**{game}**")
            st.code(str(ch.path))
            st.write({"exists": ch.exists, "size_bytes": ch.size_bytes, "rows": ch.rows, "note": ch.note})
            if ch.note in ("empty file", "no rows"):
                if st.button(f"Repair {game}"):
                    if delete_if_empty(ch.path):
                        st.success("Empty file removed. Use Refresh to re-create.")
                    else:
                        st.info("File not empty or could not delete.")

    st.divider()
    st.subheader("Refresh Caches")
    from programs.features.refresh import refresh_all, refresh_one
    if st.button("Refresh ALL now"):
        with st.spinner("Refreshing all games..."):
            res = refresh_all(root)
        st.success("Refresh attempted. See details below.")
        st.json({k: str(v) for k, v in res.items()})
    for game in GAME_TO_CACHE.keys():
        if st.button(f"Refresh {game}"):
            with st.spinner(f"Refreshing {game}..."):
                r = refresh_one(root, game)
            st.success(f"{game}: draws added {getattr(r,'draws_added', '?')} (source {getattr(r,'source_used','?')}).")

with tab2:
    st.subheader("Analytics")
    st.caption("Evaluate caches and trigger targeted refresh from one place.")
    from programs.features.health import GAME_TO_CACHE, check_one
    from programs.features.refresh import refresh_one
    import pandas as pd

    # Build a compact summary table
    rows = []
    for g in GAME_TO_CACHE.keys():
        ch = check_one(root, g)
        rows.append({"Game": g, "Rows": ch.rows, "Note": ch.note or "", "Path": str(ch.path)})
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch")

    st.write("")
    cols = st.columns(3)
    with cols[0]:
        game_sel = st.selectbox("Refresh a game", list(GAME_TO_CACHE.keys()))
        if st.button("Run Refresh", key="analytics_refresh_one"):
            with st.spinner(f"Refreshing {game_sel}..."):
                r = refresh_one(root, game_sel)
            st.success(f"{game_sel}: draws added {getattr(r,'draws_added','?')} (source {getattr(r,'source_used','?')}).")
    with cols[1]:
        if st.button("Refresh ALL (Analytics)", key="analytics_refresh_all"):
            from programs.features.refresh import refresh_all
            with st.spinner("Refreshing all games..."):
                res = refresh_all(root)
            st.success("Refresh attempted. See below.")
            st.json({k: str(v) for k, v in res.items()})
    with cols[2]:
        st.info("Tip: Use Tools tab for health & maintenance tasks.")

with tab3:
    st.subheader("Training & Evaluation")
    st.caption("Train models and view evaluation status.")
    try:
        from programs.utils.model_trainers import GAMES, train_all_for_game  # type: ignore
        from programs.utils.model_eval import evaluate_game  # type: ignore
        gsel = st.selectbox("Game", options=list(GAMES))
        if st.button("Train All Models for Game"):
            with st.spinner(f"Training {gsel}..."):
                train_all_for_game(root, gsel)
            st.success("Training complete.")
        if st.button("Evaluate Selected Game"):
            with st.spinner(f"Evaluating {gsel}..."):
                res = evaluate_game(root, gsel)
            st.write(gsel, {"cache_exists": res.get("cache_exists"), "rows": res.get("cache_draws"), "models": res.get("models")})
    except Exception as e:
        st.info(f"Eval helpers not found or failed: {e}")

with tab4:
    st.subheader("Maintenance Tools")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.caption("Project Health")
        try:
            from programs.tools.health_check import scan
            if st.button("Scan for syntax/ellipsis issues"):
                with st.spinner("Scanning project..."):
                    msg = scan(root)
                st.code(msg)
        except Exception as e:
            st.info(f"Health scan not available: {e}")

    with c2:
        st.caption("Page Cleanup")
        try:
            from programs.maintenance.page_consolidator import consolidate_pages
            if st.button("Consolidate Sidebar Pages"):
                out = consolidate_pages(root)
                st.success("Consolidation complete.")
                st.json(out)
                st.warning("Restart the app to see changes.")
        except Exception as e:
            st.info(f"Page consolidator not available: {e}")

    with c3:
        st.caption("Cache Ops")
        from programs.features.refresh import refresh_all
        if st.button("Refresh ALL Caches (Tools)"):
            with st.spinner("Refreshing all games..."):
                res = refresh_all(root)
            st.success("Refresh attempted. See details below.")
            st.json({k: str(v) for k, v in res.items()})



# ================= Local LLMs (GPT4All, .gguf) =================
import streamlit as _st

_st.divider()
_st.subheader("Local LLMs (GPT4All, .gguf)")
_st.caption("Optional. Point to a folder with .gguf models; we'll auto-pick the best instruct model.")

try:
    from programs.services import local_llm as _llm
    cfg = _llm.get_config()
    path_in = _st.text_input("Model directory", value=cfg.get("model_dir",""), placeholder=r"C:\\Models\\GGUF   or   /mnt/models/gguf")
    c1, c2, c3, c4 = _st.columns(4)
    with c1:
        if _st.button("Save path", key="llm_save"):
            _llm.set_model_dir(path_in); _st.success("Saved path.")
    with c2:
        if _st.button("Scan", key="llm_scan"):
            _st.session_state["_llm_scan_models"] = _llm.list_models(path_in)
    with c3:
        if _st.button("Auto-pick best now", key="llm_autopick"):
            models = _st.session_state.get("_llm_scan_models", _llm.list_models(path_in))
            if models:
                best = _llm.suggest_best_model(models)
                if best:
                    _llm.set_preferred_model(best); _st.success(f"Preferred model set to: {best}")
            else:
                _st.warning("No models found. Click Scan first.")
    with c4:
        if _st.button("Clear preferred", key="llm_clear"):
            _llm.set_preferred_model(""); _st.success("Cleared preferred model.")

    models = _st.session_state.get("_llm_scan_models", _llm.list_models(path_in))
    if models:
        ranked = _llm.rank_models(models)
        _st.table({"Model": [m for m,_ in ranked], "Score": [round(s,2) for _,s in ranked]})
        sel = _st.selectbox("Override preferred model", options=[m for m,_ in ranked])
        if _st.button("Set selected as preferred", key="llm_set_pref"):
            _llm.set_preferred_model(sel); _st.success(f"Preferred model set to: {sel}")
    else:
        _st.info("No .gguf files found in the selected folder.")

    _st.write("—")
    _st.write("Status")
    _st.json(_llm.status())
    if _st.button("Test model (~2s)", key="llm_test"):
        try:
            m = _llm.open_model()
            if m is None:
                _st.warning("No model available. Install gpt4all (pip install gpt4all) and verify folder.")
            else:
                with m.chat_session():
                    out = m.generate("Say 'ready' in one word.", max_tokens=6, temp=0.1)
                _st.success(f"Model responded: {out!r}")
        except Exception as e:
            _st.error(f"Test failed: {e}")
except Exception as e:
    _st.info(f"LLM controls unavailable: {e}")
