Param(
  [string]$RepoRoot = ".",
  [string]$AstroSubdir = "AstroLotto",
  [string]$Programs = "programs"  # as per your error path
)

function Fail($m){ Write-Error $m; exit 1 }

$RepoRoot = Resolve-Path $RepoRoot | % Path
$AstroDir = Join-Path $RepoRoot $AstroSubdir
$ProgDir = Join-Path $AstroDir $Programs

if (!(Test-Path $ProgDir)) { Fail "AstroLotto programs folder not found: $ProgDir" }

$Targets = Get-ChildItem -Path $ProgDir -Filter app_main.py -Recurse -File
if ($Targets.Count -eq 0) { Fail "Could not find app_main.py under $ProgDir" }

foreach ($t in $Targets) {
  $path = $t.FullName
  $txt = Get-Content $path -Raw
  $orig = $txt

  # Ensure we have streamlit import
  if ($txt -notmatch "import streamlit as st") {
    $txt = "import streamlit as st`r`n" + $txt
  }

  # 1) Replace any @st.cache_data on load_kernel with @st.cache_resource
  $txt = [regex]::Replace($txt, "@st\.cache_data\s*\(([^)]*)\)\s*(\r?\n\s*def\s+load_kernel\s*\()", "@st.cache_resource($1)`r`n`$2")
  $txt = [regex]::Replace($txt, "@st\.cache_data\s*(\r?\n\s*def\s+load_kernel\s*\()", "@st.cache_resource()`r`n`$1")

  # 2) If load_kernel has no decorator, add cache_resource above it
  if ($txt -match "^\s*def\s+load_kernel\s*\(" -and $txt -notmatch "@st\.cache_resource[^\r\n]*\r?\n\s*def\s+load_kernel\s*\(") {
    $txt = [regex]::Replace($txt, "^\s*def\s+load_kernel\s*\(", "@st.cache_resource()`r`n`0", "Multiline")
  }

  if ($txt -ne $orig) {
    Set-Content -Path $path -Value $txt -Encoding UTF8
    Write-Host "Patched:" ($path.Replace($RepoRoot + '\',''))
  } else {
    Write-Host "No changes needed:" ($path.Replace($RepoRoot + '\',''))
  }
}