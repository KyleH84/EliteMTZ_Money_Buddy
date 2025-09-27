# scripts\install_hook.ps1
Param(
  [string]$RepoRoot = "."
)

$hookSrc = Join-Path $RepoRoot ".githooks\pre-commit"
$hookDstDir = Join-Path $RepoRoot ".git\hooks"
$hookDst = Join-Path $hookDstDir "pre-commit"

if (!(Test-Path $hookSrc)) {
    Write-Error "Hook source not found: $hookSrc"
    exit 1
}
if (!(Test-Path $hookDstDir)) {
    Write-Error "Not a Git repo (missing .git/hooks). Run inside a cloned repo."
    exit 1
}

Copy-Item $hookSrc $hookDst -Force
Write-Host "Installed pre-commit hook to $hookDst"
