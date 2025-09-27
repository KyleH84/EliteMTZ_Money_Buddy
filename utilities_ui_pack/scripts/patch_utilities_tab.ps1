Param(
  [string]$RepoRoot = ".",
  [string]$AppSubdir = "BreakoutBuddy",
  [string]$AppProg = "program"
)

function Fail($m){ Write-Error $m; exit 1 }

$RepoRoot = Resolve-Path $RepoRoot | % Path
$AppDir = Join-Path $RepoRoot $AppSubdir
$ProgDir = Join-Path $AppDir $AppProg

if (!(Test-Path $ProgDir)) { Fail "App folder not found: $ProgDir" }

# Ensure panel file exists in modules/utilities/
$UtilDir = Join-Path $ProgDir "modules/utilities"
if (!(Test-Path $UtilDir)) { New-Item -ItemType Directory -Path $UtilDir | Out-Null }
$PanelPath = Join-Path $UtilDir "reporting_fixed_panel.py"
if (!(Test-Path $PanelPath)) { Fail "Panel file missing: $PanelPath (copy pack first)" }

# Find Utilities tab file under modules/tabs
$TabsDir = Join-Path $ProgDir "modules/tabs"
if (!(Test-Path $TabsDir)) { Fail "Tabs dir not found: $TabsDir" }

$Candidates = Get-ChildItem -Path $TabsDir -Filter *.py -File | Where-Object {
  (Select-String -Path $_.FullName -Pattern "Utilities|UTILITIES|utilities" -Quiet)
}

if ($Candidates.Count -eq 0) {
  Fail "Could not locate a Utilities tab file in $TabsDir. Open the file name for Utilities tab and rerun."
}

foreach ($file in $Candidates) {
  $txt = Get-Content $file.FullName -Raw
  $changed = $false

  if ($txt -notmatch "from modules\.utilities\.reporting_fixed_panel import render_reporting_fixed_panel") {
    $txt = "from modules.utilities.reporting_fixed_panel import render_reporting_fixed_panel`r`n" + $txt
    $changed = $true
  }

  # Try to inject render call near the end of the Utilities render function.
  # Heuristics: look for a function starting with 'def render' that mentions 'Utilities' in a header line or section.
  # Fallback: append a call at end of file.
  $pattern = "(def\s+render[^\n]*\:[\s\S]*?)$"
  if ($txt -match $pattern) {
    # Append our panel call at the end of the file if not already present
    if ($txt -notmatch "render_reporting_fixed_panel\(") {
      $txt = $txt + "`r`n`r`n# Auto-wired panel`r`nrender_reporting_fixed_panel()`r`n"
      $changed = $true
    }
  } else {
    if ($txt -notmatch "render_reporting_fixed_panel\(") {
      $txt = $txt + "`r`n`r`n# Auto-wired panel`r`nrender_reporting_fixed_panel()`r`n"
      $changed = $true
    }
  }

  if ($changed) {
    Set-Content -Path $file.FullName -Value $txt -Encoding UTF8
    Write-Host "Patched Utilities tab:" ($file.FullName.Replace($RepoRoot + '\',''))
  } else {
    Write-Host "Utilities tab already wired:" ($file.FullName.Replace($RepoRoot + '\',''))
  }
}