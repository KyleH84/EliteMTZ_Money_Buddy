from __future__ import annotations
import re
from pathlib import Path

# Packages to fix
TARGET_DIRS = [
    Path("AstroLotto/programs"),
    Path("BreakoutBuddy/program"),
    Path("BreakoutBuddy/program/modules"),
]

from_stmt = re.compile(r'^\s*from\s+([A-Za-z_][A-Za-z0-9_]*)\s+import\s+', re.M)

def fix_dir(pkg_dir: Path) -> int:
    if not pkg_dir.exists():
        return 0
    # discover sibling module names in this directory
    module_names = set(p.stem for p in pkg_dir.glob("*.py") if p.name != "__init__.py")
    changed = 0
    for py in pkg_dir.rglob("*.py"):
        if py.name == "__init__.py":
            continue
        text = py.read_text(encoding="utf-8")
        def repl(m):
            name = m.group(1)
            # skip future imports or real packages
            if name in module_names:
                return f"from .{name} import "
            return m.group(0)
        new = from_stmt.sub(repl, text)
        if new != text:
            py.write_text(new, encoding="utf-8")
            changed += 1
    return changed

total = 0
for d in TARGET_DIRS:
    total += fix_dir(d)

print(f"Patched files: {total}")