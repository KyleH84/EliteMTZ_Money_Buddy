Param(
  [string]$RepoRoot = ".",
  [string]$Remote = "origin",
  [string]$Branch = "main"
)

function Ensure-InRepo {
  if (!(Test-Path (Join-Path $RepoRoot ".git"))) {
    Write-Error "Not a git repo: $RepoRoot (missing .git). Open the script in your repo root."
    exit 1
  }
}

function Expand-ZipIfPresent($zipName) {
  $zipPath = Join-Path $RepoRoot $zipName
  if (Test-Path $zipPath) {
    Write-Host "Unpacking $zipName ..."
    Expand-Archive -Path $zipPath -DestinationPath $RepoRoot -Force
  } else {
    Write-Host "Skipping $zipName (not found)."
  }
}

function Inject-HealthWidget($filePath) {
  if (!(Test-Path $filePath)) { return }
  $text = Get-Content $filePath -Raw
  if ($text -notmatch "from utilities\.health_widget import render_health_widget") {
    $text = "from utilities.health_widget import render_health_widget`r`n" + $text
  }
  if ($text -notmatch "render_health_widget\(") {
    # call it near the top (harmless if called twice per run)
    $text = $text -replace "(import streamlit as st[^\r\n]*\r?\n)", "`$1`r`nrender_health_widget()`r`n"
    if ($text -notmatch "render_health_widget\(") {
      # fallback: just prefix the call
      $text = "render_health_widget()`r`n" + $text
    }
  }
  Set-Content -Path $filePath -Value $text -Encoding UTF8
  Write-Host "Injected health widget into $filePath"
}

function New-ReportingFixedPage {
  $pagesDir = Join-Path $RepoRoot "pages"
  if (!(Test-Path $pagesDir)) { New-Item -ItemType Directory -Path $pagesDir | Out-Null }
  $target = Join-Path $pagesDir "Reporting_Fixed.py"
  $content = @"
import streamlit as st
import pandas as pd

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
    spy = get_spy_prices()  # yfinance real data, cached
except Exception as e:
    st.warning(f"SPY loader failed ({type(e).__name__}): {e}. RelSPY will remain empty.")
    spy = None

df = fill_feature_gaps(df, spy_ref=spy)
st.dataframe(df.head(50), use_container_width=True)

st.subheader("Feature gap audit")
st.dataframe(report_feature_gaps(df), use_container_width=True)
"@
  Set-Content -Path $target -Value $content -Encoding UTF8
  Write-Host "Created pages/Reporting_Fixed.py"
}

function Install-PreCommit {
  $hookSrc = Join-Path $RepoRoot ".githooks\pre-commit"
  $hookDstDir = Join-Path $RepoRoot ".git\hooks"
  $hookDst = Join-Path $hookDstDir "pre-commit"
  if (Test-Path $hookSrc) {
    Copy-Item $hookSrc $hookDst -Force
    Write-Host "Installed .git/hooks/pre-commit"
  } else {
    Write-Host "No .githooks/pre-commit found; skipping guard."
  }
}

# --- MAIN ---

Set-Location $RepoRoot
Ensure-InRepo

# 1) Unpack packs (safe: only adds/overwrites files from the zips)
Expand-ZipIfPresent "caching_fix_pack.zip"
Expand-ZipIfPresent "health_feature_pack.zip"
Expand-ZipIfPresent "wiring_fix_pack.zip"

# 2) Install pre-commit guard (prevents bad cache decorators on future commits)
Install-PreCommit

# 3) Create Reporting_Fixed page that uses the new plumbing
New-ReportingFixedPage

# 4) Add health widget to common entrypoints if found
Inject-HealthWidget (Join-Path $RepoRoot "streamlit_app.py")
Inject-HealthWidget (Join-Path $RepoRoot "home_main.py")

# 5) Run caching auto-fixer (resources -> cache_resource; data -> cache_data)
if (Test-Path (Join-Path $RepoRoot "fix_streamlit_caching.py")) {
  Write-Host "Running caching fixer..."
  python .\fix_streamlit_caching.py .
} else {
  Write-Host "fix_streamlit_caching.py not found (caching pack not unpacked?)"
}

# 6) Pull, commit, push
git remote set-url $Remote https://github.com/KyleH84/EliteMTZ_Money_Buddy.git
git fetch $Remote
git checkout $Branch
git pull $Remote $Branch --allow-unrelated-histories

git add -A
$commitMsg = "Wire health widget, real-data reporting page, watchlist backend, caching fix"
git commit -m $commitMsg
git push $Remote $Branch

Write-Host "`n✅ Done. Streamlit Cloud should auto-redeploy from GitHub."
