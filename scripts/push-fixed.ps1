# scripts\push-fixed.ps1
Param(
  [string]$RepoRoot = ".",
  [string]$Remote = "origin",
  [string]$Branch = "main"
)

Set-Location $RepoRoot

# Run the caching fixer
python .\fix_streamlit_caching.py .

# Optional: ensure remote URL is set correctly (edit if needed)
# git remote set-url $Remote https://github.com/KyleH84/EliteMTZ_Money_Buddy.git

git pull $Remote $Branch --allow-unrelated-histories
git add -A
$msg = "Fix Streamlit caching (resource vs data) + sync on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
git commit -m $msg
git push $Remote $Branch
