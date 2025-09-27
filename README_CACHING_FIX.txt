CACHING FIX PACK — Streamlit resource vs data caching
=====================================================

What this does
--------------
1) Adds helper decorators you can import everywhere:
   - utilities/caching.py -> cache_data() and cache_resource() with sane defaults.

2) Provides an auto-fixer script:
   - fix_streamlit_caching.py: scans your repo and flips @st.cache_data to @st.cache_resource
     ONLY on functions that look like resource factories (load_/open_/connect_/get_*_client, etc.).

3) Provides a pre-commit safety net:
   - .githooks/pre-commit: blocks commits if someone decorates a resource-like function with @st.cache_data.

4) Optional push helper:
   - scripts/push-fixed.ps1: runs the fixer, commits, and pushes to your remote branch in one go.


How to install (once)
---------------------
1) Unzip this pack into the ROOT of your repo (same folder as streamlit_app.py).
   You should see these new files:
     utilities/caching.py
     fix_streamlit_caching.py
     .githooks/pre-commit
     scripts/install_hook.ps1
     scripts/push-fixed.ps1
     README_CACHING_FIX.txt

2) Install the Git pre-commit hook (optional but recommended):
   PowerShell (from repo root):
     powershell -ExecutionPolicy Bypass -File .\scripts\install_hook.ps1 .

   If you're on Git Bash/macOS/Linux:
     cp .githooks/pre-commit .git/hooks/pre-commit
     chmod +x .git/hooks/pre-commit

3) Run the auto-fixer once:
   PowerShell (from repo root):
     python .\fix_streamlit_caching.py .

   This updates files in-place. Review the console output to see what changed.

4) Commit and push:
   PowerShell:
     git add -A
     git commit -m "Fix Streamlit caching (resource vs data)"
     git push origin main

   OR just run:
     powershell -ExecutionPolicy Bypass -File .\scripts\push-fixed.ps1 .


How to use in code going forward
--------------------------------
In your modules:
  from utilities.caching import cache_data, cache_resource

  @cache_resource()
  def load_kernel(...):   # returns ephemeris/skyfield wrapper, DB conn, client, model, etc.
      ...

  @cache_data()
  def fetch_jackpots(...):  # returns DataFrame/dict/list/str/numbers — i.e., pickle-friendly
      ...

Rule of thumb that works:
  - cache_resource for objects/resources kept around
  - cache_data for plain data you can pickle


Rollback
--------
If you need to undo the fixer changes, use Git:
  git checkout -- <file>    # restore a specific file
  git reset --hard HEAD~1   # undo the last commit entirely (careful)
