
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# astro_doctor.py - environment checks
import os, sys, importlib, platform, shutil
from pathlib import Path

def check_import(name):
    try:
        m = importlib.import_module(name)
        return True, getattr(m, "__version__", "unknown")
    except Exception as e:
        return False, str(e)

def main():
    print("=== Astro Doctor ===")
    print("cwd:", os.getcwd())
    print("python:", sys.version.replace("\n"," "))
    print("platform:", platform.platform())
    print("\n[Files]")
    for f in ["app_main.py", "engine/meta_selector.py", "utilities/oracle_engine.py"]:
        print(f" - {f}: {'OK' if Path(f).exists() else 'MISSING'}")
    print("\n[Imports]")
    for mod in ["streamlit","numpy","pandas","matplotlib","sklearn","requests","skyfield"]:
        ok, info = check_import(mod)
        print(f" - {mod:10s}: {'OK' if ok else 'FAIL'} ({info})")
    print("\n[Project imports]")
    for mod in ["utilities.probability","utilities.fallback_predict","engine.meta_selector"]:
        ok, info = check_import(mod)
        print(f" - {mod:28s}: {'OK' if ok else 'FAIL'} ({info})")
    print("\nIf a project import FAILs, you likely didn’t unzip all files into the same folder as app_main.py.")
    print("If streamlit FAILs, install it with:  pip install -r requirements_min.txt  (from this folder).")

if __name__ == "__main__":
    main()
