@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "ROOT=%CD%"
set "VENV=%ROOT%\.venv311"
set "PY=%VENV%\Scripts\python.exe"

if not exist "%PY%" (
  echo [ERROR] venv not found at "%VENV%"
  echo Launch once with PC-RUN_AstroLotto.bat to create it, then re-run this.
  pause
  goto :END
)

"%PY%" -m pip install --upgrade pip wheel setuptools
"%PY%" -m pip install torch torchvision torchaudio

:END
pause
endlocal
