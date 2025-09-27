
Param(
  [string]$RepoRoot = ".",
  [string]$AppSubdir = "BreakoutBuddy",
  [string]$AppProg = "program",
  [string]$Remote = "origin",
  [string]$Branch = "main"
)

function Fail($msg) { Write-Error $msg; exit 1 }

function Ensure-InRepo($root) {
  if (!(Test-Path (Join-Path $root ".git"))) {
    Fail "Not a git repo: $root (missing .git). Run from the repo root."
  }
}

function Ensure-Dir($p) { if (!(Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null } }

$RepoRoot = Resolve-Path $RepoRoot | % Path
$AppDir   = Join-Path $RepoRoot $AppSubdir
$ProgDir  = Join-Path $AppDir   $AppProg

Ensure-InRepo $RepoRoot
if (!(Test-Path $ProgDir)) { Fail "App folder not found: $ProgDir" }

$RootUtils = Join-Path $RepoRoot "utilities"
$RootData  = Join-Path $RepoRoot "data"
$RootPages = Join-Path $RepoRoot "pages"
$RootScripts = Join-Path $RepoRoot "scripts"

$TargetUtils = Join-Path $ProgDir "utilities"
$TargetData  = Join-Path $ProgDir "data"
$TargetMods  = Join-Path $ProgDir "modules"

Ensure-Dir $TargetUtils
Ensure-Dir $TargetData
Ensure-Dir $TargetMods

Write-Host "=== Relocating misplaced folders INTO $ProgDir ==="

# 1) Move/merge utilities/*.py -> BreakoutBuddy/program/utilities/
if (Test-Path $RootUtils) {
  Get-ChildItem -Path $RootUtils -File -Filter *.py | ForEach-Object {
    Copy-Item $_.FullName -Destination (Join-Path $TargetUtils $_.Name) -Force
  }
}

# 2) Move data/spy_loader.py -> BreakoutBuddy/program/data/spy_loader.py
$SpySrc = Join-Path $RootData "spy_loader.py"
if (Test-Path $SpySrc) {
  Copy-Item $SpySrc -Destination (Join-Path $TargetData "spy_loader.py") -Force
}

# 3) Remove root 'pages' and 'scripts' (these should not live at repo root per reference layout)
if (Test-Path $RootPages) {
  Write-Host "Removing root pages/ (Streamlit pages belong with the entry app; reference has none at root)"
  Remove-Item $RootPages -Recurse -Force
}
if (Test-Path $RootScripts) {
  Write-Host "Removing root scripts/ (installer helpers)"
  Remove-Item $RootScripts -Recurse -Force
}

# 4) Clean up root utilities/data if they only contain files we just moved
function Remove-Dir-If-Empty($p) {
  if (Test-Path $p) {
    $items = Get-ChildItem -Path $p -Recurse -Force | Measure-Object
    if ($items.Count -eq 0) {
      Remove-Item $p -Force
    }
  }
}
# If data only had spy_loader.py, remove it; otherwise leave it
if (Test-Path $RootData) {
  $others = Get-ChildItem -Path $RootData -Recurse -File | Where-Object { $_.Name -ne "spy_loader.py" }
  if ($others.Count -eq 0) {
    Remove-Item $RootData -Recurse -Force
  }
}
# Remove root utilities entirely after copy
if (Test-Path $RootUtils) {
  Remove-Item $RootUtils -Recurse -Force
}

# 5) Patch root streamlit_app.py to import health widget safely AFTER ensuring BreakoutBuddy/program on sys.path if needed
$RootApp = Join-Path $RepoRoot "streamlit_app.py"
if (Test-Path $RootApp) {
  $text = Get-Content $RootApp -Raw

  # Remove any early import/call we previously injected
  $text = $text -replace "^\s*from utilities\.health_widget import render_health_widget\s*?
", ""
  $text = $text -replace "^\s*render_health_widget\(\)\s*?
", ""

  # Inject safe import block near the top (after __future__ if present, else at line 1)
  $block = @"
# --- Health widget (BreakoutBuddy-aware import) ---
try:
    from utilities.health_widget import render_health_widget  # either root-level utilities or already on sys.path
except Exception:
    import sys
    from pathlib import Path as _Path
    _bb_prog = _Path(__file__).parent / "BreakoutBuddy" / "program"
    if _bb_prog.exists() and str(_bb_prog) not in sys.path:
        sys.path.insert(0, str(_bb_prog))
    from utilities.health_widget import render_health_widget  # now import from BreakoutBuddy/program
try:
    render_health_widget()
except Exception as _hw_e:
    print("Health widget init warning:", _hw_e)
# --- end health widget ---

"@

  if ($text -match "from __future__ import") {
    # insert after the __future__ import line
    $text = $text -replace "(from __future__ import[^
]*?
)", "`$1$block"
  } else {
    $text = "$block$text"
  }

  Set-Content -Path $RootApp -Value $text -Encoding UTF8
  Write-Host "Patched health widget import/call in streamlit_app.py"
}

# 6) Ensure watchlist storage API exists in BreakoutBuddy/program/modules/watchlist.py
$AppWatch = Join-Path $TargetMods "watchlist.py"
if (Test-Path $AppWatch) {
  $wtxt = Get-Content $AppWatch -Raw
  if ($wtxt -notmatch "def\s+read_watchlist\s*\(") {
    $append = @'
# --- Appended storage helpers (added by layout repair) ---
# Simple watchlist storage using DuckDB (preferred) or CSV fallback.
import os, csv
_WATCHLIST_CSV = os.path.join("Data", "watchlist.csv")
try:
    import duckdb as _duckdb
    _HAVE_DUCK = True
except Exception:
    _HAVE_DUCK = False
_DB_PATH = os.path.join("Data", "watchlist.duckdb")

def _ensure_dirs():
    os.makedirs("Data", exist_ok=True)

def _ensure_duck():
    if not _HAVE_DUCK:
        return None
    con = _duckdb.connect(_DB_PATH, read_only=False)
    con.execute("""CREATE TABLE IF NOT EXISTS watchlist(symbol TEXT PRIMARY KEY, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);""")
    return con

def read_watchlist():
    _ensure_dirs()
    if _HAVE_DUCK:
        con = _ensure_duck()
        rows = con.execute("SELECT symbol FROM watchlist ORDER BY symbol").fetchall()
        con.close()
        return [r[0] for r in rows]
    if not os.path.exists(_WATCHLIST_CSV):
        return []
    with open(_WATCHLIST_CSV, newline='') as f:
        return [row[0] for row in csv.reader(f) if row]

def write_watchlist(symbols):
    _ensure_dirs()
    symbols = sorted(set((s or "").upper().strip() for s in symbols if s))
    if _HAVE_DUCK:
        con = _ensure_duck()
        con.execute("DELETE FROM watchlist")
        con.executemany("INSERT INTO watchlist(symbol) VALUES (?)", [(s,) for s in symbols])
        con.close()
        return
    with open(_WATCHLIST_CSV, 'w', newline='') as f:
        w = csv.writer(f); [w.writerow([s]) for s in symbols]

def add_to_watchlist(symbol):
    s = (symbol or "").upper().strip()
    if not s: return
    if _HAVE_DUCK:
        con = _ensure_duck()
        con.execute("INSERT OR REPLACE INTO watchlist(symbol) VALUES (?)", [s])
        con.close()
    else:
        cur = set(read_watchlist()); cur.add(s); write_watchlist(list(cur))

def remove_from_watchlist(symbol):
    s = (symbol or "").upper().strip()
    if not s: return
    if _HAVE_DUCK:
        con = _ensure_duck()
        con.execute("DELETE FROM watchlist WHERE symbol = ?", [s])
        con.close()
    else:
        cur = set(read_watchlist()); cur.discard(s); write_watchlist(list(cur))
# --- end appended helpers ---

'@
    Add-Content -Path $AppWatch -Value $append -Encoding UTF8
    Write-Host "Appended read/write/add/remove watchlist helpers into modules/watchlist.py"
  } else {
    Write-Host "modules/watchlist.py already has read_watchlist(); leaving as-is."
  }
}

# 7) Run caching fixer inside BreakoutBuddy/program if present
$AppFixer = Join-Path $ProgDir "fix_streamlit_caching.py"
if (Test-Path $AppFixer) {
  Write-Host "Running caching fixer in $ProgDir ..."
  python $AppFixer $ProgDir
}

# 8) Commit & push
Set-Location $RepoRoot
git remote set-url $Remote https://github.com/KyleH84/EliteMTZ_Money_Buddy.git
git fetch $Remote
git checkout $Branch
git pull $Remote $Branch --allow-unrelated-histories

git add -A
$commitMsg = "Align layout with reference: move utils/data into BreakoutBuddy/program, patch health widget import, add watchlist storage API, clean root pages/scripts"
git commit -m $commitMsg
git push $Remote $Branch

Write-Host "`n✅ Repair complete. Files now live under BreakoutBuddy/program; root is clean. Streamlit Cloud should auto-redeploy."
