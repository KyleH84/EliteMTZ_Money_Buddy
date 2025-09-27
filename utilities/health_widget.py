# utilities/health_widget.py
import os, glob, time, contextlib
import streamlit as st
try:
    import duckdb
except Exception:
    duckdb = None

@st.cache_data(ttl=60)
def _cache_probe(x:int)->float:
    return time.time()

def _probe_cache_ok()->bool:
    return _cache_probe(1) == _cache_probe(1)

def _find_duckdb_file(root_candidates=("Data","data",".")) -> str | None:
    for root in root_candidates:
        matches = glob.glob(os.path.join(root, "**", "*.duckdb"), recursive=True)
        if matches:
            matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return matches[0]
    return None

def _probe_duckdb(db_path: str | None):
    if duckdb is None:
        return (False, "duckdb not installed")
    try:
        if db_path is None:
            return (False, "no .duckdb file found")
        con = duckdb.connect(db_path, read_only=False)
        with contextlib.closing(con):
            con.execute("CREATE TABLE IF NOT EXISTS _mb_health (ts TIMESTAMP)")
            con.execute("INSERT INTO _mb_health VALUES (CURRENT_TIMESTAMP)")
            con.execute("SELECT COUNT(*) FROM _mb_health")
            count = con.fetchone()[0]
        return (True, f"OK (rows: {count})")
    except Exception as e:
        return (False, f"{type(e).__name__}: {e}")

def _probe_supabase_config():
    url = os.getenv("SUPABASE_URL") or (st.secrets.get("SUPABASE_URL") if hasattr(st, "secrets") else None)
    key = os.getenv("SUPABASE_KEY") or (st.secrets.get("SUPABASE_KEY") if hasattr(st, "secrets") else None)
    if url and key: return (True, "configured")
    if url or key:  return (False, "partial (one missing)")
    return (False, "not set")

def render_health_widget():
    with st.sidebar.expander("⚙️ Cache & Storage Health", expanded=False):
        st.write("**Cache (st.cache_*)**:", "✅ working" if _probe_cache_ok() else "❌ not working")
        db_path = _find_duckdb_file()
        ok,msg = _probe_duckdb(db_path)
        st.write("**DuckDB**:", "✅" if ok else "❌", msg, "(file:", db_path or "none", ")")
        ok_s,msg_s = _probe_supabase_config()
        st.write("**Supabase secrets**:", "✅" if ok_s else "❌", msg_s)
        st.caption("Rule: resources -> cache_resource(); data -> cache_data().")