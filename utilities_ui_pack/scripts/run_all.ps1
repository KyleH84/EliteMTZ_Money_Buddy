Param(
  [string]$RepoRoot = ".",
  [string]$Remote = "origin",
  [string]$Branch = "main",
  [string]$AppSubdir = "BreakoutBuddy",
  [string]$AppProg = "program"
)

function Fail($m){ Write-Error $m; exit 1 }

$RepoRoot = Resolve-Path $RepoRoot | % Path
if (!(Test-Path (Join-Path $RepoRoot ".git"))) { Fail "Not a git repo: $RepoRoot" }

$AppDir = Join-Path $RepoRoot $AppSubdir
$ProgDir = Join-Path $AppDir $AppProg
if (!(Test-Path $ProgDir)) { Fail "App folder not found: $ProgDir" }

# Ensure modules/utilities exists and drop in the panel file
$UtilDir = Join-Path $ProgDir "modules/utilities"
if (!(Test-Path $UtilDir)) { New-Item -ItemType Directory -Path $UtilDir | Out-Null }
$PanelSource = Join-Path $RepoRoot "modules/utilities/reporting_fixed_panel.py"
if (!(Test-Path $PanelSource)) { Fail "Panel source missing at repo root: $PanelSource. Copy pack to repo root or specify correct location." }
Copy-Item $PanelSource -Destination (Join-Path $UtilDir "reporting_fixed_panel.py") -Force

# Run the utilities tab patcher
powershell -ExecutionPolicy Bypass -File ".\scripts\patch_utilities_tab.ps1" -RepoRoot $RepoRoot -AppSubdir $AppSubdir -AppProg $AppProg

# Fix AstroLotto cache decorator
powershell -ExecutionPolicy Bypass -File ".\scripts\fix_astrolotto_cache.ps1" -RepoRoot $RepoRoot

# Commit & push
Set-Location $RepoRoot
git remote set-url $Remote https://github.com/KyleH84/EliteMTZ_Money_Buddy.git
git fetch $Remote
git checkout $Branch
git pull $Remote $Branch --allow-unrelated-histories
git add -A
git commit -m "Wire Reporting Fixed into Utilities tab + fix AstroLotto load_kernel caching"
git push $Remote $Branch

Write-Host "`n✅ Done. Utilities tab now includes Reporting (Fixed), and AstroLotto kernel uses cache_resource."