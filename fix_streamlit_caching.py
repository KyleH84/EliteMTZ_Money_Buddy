# fix_streamlit_caching.py
# Usage: python fix_streamlit_caching.py .
# Finds functions that look like "resources" and replaces @st.cache_data(...) with @st.cache_resource(...).
import os, re, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."

RESOURCE_PREFIXES = (
    "load_", "open_", "connect_", "get_ephemeris", "get_skyfield",
    "get_duckdb", "open_duckdb", "get_db", "get_connection", "get_client",
    "init_", "build_model", "load_model", "make_client", "create_client",
)

def looks_like_resource(def_line: str) -> bool:
    m = re.match(r"\s*def\s+([a-zA-Z0-9_]+)\s*\(", def_line)
    if not m: return False
    return m.group(1).startswith(RESOURCE_PREFIXES)

changed = 0
for base, _, files in os.walk(ROOT):
    for f in files:
        if not f.endswith(".py"):
            continue
        path = os.path.join(base, f)
        try:
            txt = open(path, "r", encoding="utf-8", errors="ignore").read()
        except Exception:
            continue

        lines = txt.splitlines()
        out, i, modified = [], 0, False
        while i < len(lines):
            line = lines[i]
            if "@st.cache_data" in line:
                # Look ahead for the def this decorator applies to
                j = i + 1
                while j < len(lines) and (lines[j].strip() == "" or lines[j].lstrip().startswith("@")):
                    j += 1
                if j < len(lines) and lines[j].lstrip().startswith("def") and looks_like_resource(lines[j]):
                    repl = re.sub(r"@st\.cache_data\([^)]*\)", "@st.cache_resource(show_spinner=False)", line)
                    if repl == line:
                        repl = "@st.cache_resource(show_spinner=False)"
                    out.append(repl)
                    modified = True
                    i += 1
                    continue
            out.append(line)
            i += 1

        if modified:
            with open(path, "w", encoding="utf-8") as w:
                w.write("\n".join(out))
            changed += 1
            print("Updated:", path)

print(f"Done. Files updated: {changed}")
