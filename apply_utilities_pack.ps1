
Param(
  [string]$RepoRoot = ".",
  [string]$PackDir = "utilities_ui_pack",
  [string]$Remote = "origin",
  [string]$Branch = "main",
  [switch]$Cleanup
)

function Fail($m){ Write-Error $m; exit 1 }

$RepoRoot = Resolve-Path $RepoRoot | % Path
if (!(Test-Path (Join-Path $RepoRoot ".git"))) { Fail "Not a git repo: $RepoRoot" }

# Locate the pack folder (by name) if not at expected relative path
$PackPath = Join-Path $RepoRoot $PackDir
if (!(Test-Path $PackPath)) {
  $hit = Get-ChildItem -Path $RepoRoot -Recurse -Directory -Filter "utilities_ui_pack" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($hit) { $PackPath = $hit.FullName } else { Fail "Couldn't find utilities_ui_pack under $RepoRoot" }
}

# Validate expected files inside the pack
$PanelSrc = Join-Path $PackPath "modules\utilities\reporting_fixed_panel.py"
$PatchTab = Join-Path $PackPath "scripts\patch_utilities_tab.ps1"
$FixAstro = Join-Path $PackPath "scripts\fix_astrolotto_cache.ps1"

foreach ($p in @($PanelSrc,$PatchTab,$FixAstro)) { if (!(Test-Path $p)) { Fail "Missing file in pack: $p" } }

# Target: BreakoutBuddy/program
$AppDir = Join-Path $RepoRoot "BreakoutBuddy"
$ProgDir = Join-Path $AppDir "program"
if (!(Test-Path $ProgDir)) { Fail "App folder not found: $ProgDir" }

# Ensure target utilities dir
$TargetUtilDir = Join-Path $ProgDir "modules\utilities"
if (!(Test-Path $TargetUtilDir)) { New-Item -ItemType Directory -Path $TargetUtilDir | Out-Null }

# Copy the panel into the app
Copy-Item $PanelSrc -Destination (Join-Path $TargetUtilDir "reporting_fixed_panel.py") -Force
Write-Host "Copied reporting_fixed_panel.py into BreakoutBuddy/program/modules/utilities/"

# Wire panel into Utilities tab
powershell -ExecutionPolicy Bypass -File $PatchTab -RepoRoot $RepoRoot -AppSubdir "BreakoutBuddy" -AppProg "program"

# Fix AstroLotto cache decorator
powershell -ExecutionPolicy Bypass -File $FixAstro -RepoRoot $RepoRoot

# Commit & push
Set-Location $RepoRoot
git remote set-url $Remote https://github.com/KyleH84/EliteMTZ_Money_Buddy.git
git fetch $Remote
git checkout $Branch
git pull $Remote $Branch --allow-unrelated-histories
git add -A
git commit -m "Utilities: add Reporting_Fixed panel + patch Utilities tab; AstroLotto: cache_resource for load_kernel"
git push $Remote $Branch

Write-Host "`n✅ Applied utilities_ui_pack. Utilities tab now includes Reporting (Fixed), and AstroLotto kernel cache fixed."

if ($Cleanup) {
  Write-Host "Cleaning up utilities_ui_pack..."
  Remove-Item $PackPath -Recurse -Force
}
