# smoke_test.py — import/compile every module, report errors, optional light calls.
from __future__ import annotations
import os, sys, json, importlib, runpy, traceback
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
APP_ROOT = PROJECT_DIR / "EliteMTZ_Money_Buddy"
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(APP_ROOT))

report = {"imports": {}, "summary": {}}

py_files = [Path(r)/f for r,_,fs in os.walk(APP_ROOT) for f in fs if f.endswith((".py",".pyw"))]
for p in sorted(py_files):
    rel = str(p.relative_to(PROJECT_DIR))
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        compile(txt, rel, "exec")
        # Try to import modules that look importable (skip Streamlit page files under pages/ if needed)
        mod_name = rel[:-3].replace("/", ".").replace("\\",".")
        if mod_name.endswith(".__init__"):
            mod_name = mod_name[:-9]
        ok = True
        err = ""
        try:
            importlib.invalidate_caches()
            importlib.import_module(mod_name)
        except SystemExit:
            pass
        except Exception as e:
            ok = False
            err = f"{type(e).__name__}: {e}"
        report["imports"][rel] = {"compiled": True, "imported": ok, "error": err}
    except Exception as e:
        report["imports"][rel] = {"compiled": False, "imported": False, "error": f"{type(e).__name__}: {e}"}

total = len(report["imports"])
comp_ok = sum(1 for v in report["imports"].values() if v["compiled"])
imp_ok = sum(1 for v in report["imports"].values() if v["imported"])
report["summary"] = {"files": total, "compiled_ok": comp_ok, "imported_ok": imp_ok}

out = PROJECT_DIR / "SMOKE_TEST_REPORT.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report["summary"], indent=2))
