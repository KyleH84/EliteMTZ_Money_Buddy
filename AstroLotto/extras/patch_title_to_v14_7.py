
from pathlib import Path
import os
PROJECT_DIR = Path(__file__).resolve().parent
(PROJECT_DIR / "data").mkdir(exist_ok=True, parents=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True, parents=True)

# Patch script: update visible app title to AstroLotto v14.7
from pathlib import Path
import re
# project root is one level above Extras/
root = Path(__file__).resolve().parents[1]
p = root / "programs" / "app_main.py"
s = p.read_text(encoding="utf-8")
s2 = s.replace("AstroLotto v14.6", "AstroLotto v14.7")
if s2 == s:
    s2 = re.sub(r"AstroLotto v\d+\.\d+", "AstroLotto v14.7", s)
p.write_text(s2, encoding="utf-8")
print("Updated title to AstroLotto v14.7 in", p)
