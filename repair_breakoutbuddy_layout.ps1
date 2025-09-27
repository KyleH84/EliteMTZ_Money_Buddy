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

$RepoRoot = Resolve-Path $RepoRoot | % Path
$AppDir   = Join-Path $RepoRoot $AppSubdir
$ProgDir  = Join-Path $AppDir   $AppProg

Ensure-InRepo $RepoRoot
if (!(Test-Path $ProgDir)) { Fail "App folder not found: $ProgDir" }

function Ensure-Dir($p) { if (!(Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null } }

# Target folders INSIDE BreakoutBuddy/program/
$TargetUtils = Join-Path $ProgDir "utilities"
$TargetData  = Join-Path $ProgDir "data"
$TargetMods  = Join-Path $ProgDir "modules"
$TargetPages = Join-Path $ProgDir "pages"

Ensure-Dir $TargetUtils
Ensure-Dir $TargetData
Ensure-Dir $TargetMods
Ensure-Dir $TargetPages

# Move/merge helpers that were incorrectly placed at repo root
$RootUtils = Join-Path $RepoRoot "utilities"
$RootData  = Join-Path $RepoRoot "data"
$RootMods  = Join-Path $RepoRoot "modules"
$RootPages = Join-Path $RepoRoot "pages"

Write-Host "Relocating misplaced helpers into $ProgDir ..."

# utilities/*
if (Test-Path $RootUtils) {
  Get-ChildItem -Path $RootUtils -File -Filter *.py | % {
    Copy-Item $_.FullName -Destination (Join-Path $TargetUtils $_.Name) -Force
  }
}

# data/spy_loader.py
$SpySrc = Join-Path $RootData "spy_loader.py"
if (Test-Path $SpySrc) {
  Copy-Item $SpySrc -Destination (Join-Path $TargetData "spy_loader.py") -Force
}

# modules/watchlist.py (prefer app version; replace root duplicate)
$RootWatch = Join-Path $RootMods "watchlist.py"
$AppWatch  = Join-Path $TargetMods "watchlist.py"
if (Test-Path $RootWatch) {
  # If app doesn’t have it, bring it over; otherwise keep the app one
  if (!(Test-Path $AppWatch)) {
    Copy-Item $RootWatch -Destination $AppWatch -Force
  }
  # Remove root duplicate to avoid confusion
  Remove-Item $RootWatch -Force
}

# pages/Reporting_Fixed.py -> into app pages
$RootReport = Join-Path $RootPages "Reporting_Fixed.py"
$AppReport  = Join-Path $TargetPages "Reporting_Fixed.py"
if (Test-Path $RootReport) {
  Copy-Item $RootReport -Destination $AppReport -Force
}

# fix_streamlit_caching.py: put a copy inside app program folder and run it there
$RootFixer = Join-Path $RepoRoot "fix_streamlit_caching.py"
$AppFixer  = Join-Path $ProgDir  "fix_streamlit_caching.py"
if (Test-Path $RootFixer) {
  Copy-Item $RootFixer -Destination $AppFixer -Force
}

# Ensure health widget import is present in BreakoutBuddy entrypoints if they exist
function Inject-HealthWidget($filePath) {
  if (!(Test-Path $filePath)) { return }
  $text = Get-Content $filePath -Raw
  $changed = $false
  if ($text -notmatch "from utilities\.health_widget import render_health_widget") {
    $text = "from utilities.health_widget import render_health_widget`r`n" + $text
    $changed = $true
  }
  if ($text -notmatch "render_health_widget\(") {
    if ($text -match "(import streamlit as st[^\r\n]*\r?\n)") {
      $text = $text -replace "(import streamlit as st[^\r\n]*\r?\n)", "`$1render_health_widget()`r`n"
    } else {
      $text = "render_health_widget()`r`n" + $text
    }
    $changed = $true
  }
  if ($changed) {
    Set-Content -Path $filePath -Value $text -Encoding UTF8
    Write-Host "Injected health widget into $filePath"
  }
}

# Try common BreakoutBuddy entry scripts
Inject-HealthWidget (Join-Path $AppDir "streamlit_app.py")
Inject-HealthWidget (Join-Path $AppDir "home_main.py")
Inject-HealthWidget (Join-Path $ProgDir "streamlit_app.py")
Inject-HealthWidget (Join-Path $ProgDir "home_main.py")

# Make sure Reporting_Fixed.py exists in app pages
if (!(Test-Path $AppReport)) {
  $content = @"
import streamlit as st
from utilities.health_widget import render_health_widget
from utilities.data_registry import load_active_snapshot, get_refresh_epoch
from utilities.feature_fixups import fill_feature_gaps, report_feature_gaps
from data.spy_loader import get_spy_prices

st.set_page_config(page_title="Reporting (Fixed)", layout="wide")
render_health_widget()
st.title("Reporting (Fixed)")

epoch = get_refresh_epoch()
try:
    df, path = load_active_snapshot(epoch)
except Exception as e:
    st.error(f"No data to report on: {type(e).__name__}: {e}")
    st.stop()

st.caption(f"Snapshot: {path}")

try:
    spy = get_spy_prices()
except Exception as e:
    st.warning(f"SPY loader failed ({type(e).__name__}): {e}. RelSPY will remain empty.")
    spy = None

df = fill_feature_gaps(df, spy_ref=spy)
st.dataframe(df.head(50), use_container_width=True)
st.subheader("Feature gap audit")
st.dataframe(report_feature_gaps(df), use_container_width=True)
"@
  Set-Content -Path $AppReport -Value $content -Encoding UTF8
  Write-Host "Created $($AppReport.Replace($RepoRoot + '\',''))"
}

# Run caching fixer inside BreakoutBuddy only (safe, idempotent)
if (Test-Path $AppFixer) {
  Write-Host "Running caching fixer in $ProgDir ..."
  python $AppFixer $ProgDir
}

# Git commit/push from repo root
Set-Location $RepoRoot
git remote set-url $Remote https://github.com/KyleH84/EliteMTZ_Money_Buddy.git
git fetch $Remote
git checkout $Branch
git pull $Remote $Branch --allow-unrelated-histories

git add -A
$commitMsg = "Repair layout: move helpers into BreakoutBuddy/program, fix watchlist import, add Reporting_Fixed, run caching fixer"
git commit -m $commitMsg
git push $Remote $Branch

Write-Host "`n✅ Done. Files relocated into BreakoutBuddy/program/. Streamlit Cloud should auto-redeploy."
