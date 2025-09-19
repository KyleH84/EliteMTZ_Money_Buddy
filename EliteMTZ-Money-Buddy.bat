@echo off
setlocal EnableExtensions
pushd "%~dp0"
title FRESH EliteMTZ Money Buddy

call "%~dp0CLEAN-Kylee-Paths-FORCE.bat" >nul 2>&1

set "PY_HARD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PY_HARD%" ( echo FATAL: Python 3.13 not found & pause & exit /b 1 )

if not exist ".venv_home\Scripts\python.exe" (
    "%PY_HARD%" -m venv ".venv_home" || (echo venv failed & pause & exit /b 1)
)

set "PY=%CD%\.venv_home\Scripts\python.exe"
set "PATH=%CD%\.venv_home\Scripts;%SystemRoot%\System32;%SystemRoot%"
"%PY%" -m pip install --upgrade streamlit

if exist "home_main.py" (
  "%PY%" -m streamlit run "home_main.py" --server.address 127.0.0.1 --server.port 8501
) else (
  echo home_main.py missing & pause & exit /b 1
)
popd
endlocal
