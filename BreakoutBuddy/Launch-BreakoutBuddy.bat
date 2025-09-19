@echo on
setlocal EnableExtensions
pushd "%~dp0"
title Launch BreakoutBuddy (robust)

REM ===== settings =====
set "PORT=8503"
if not "%~1"=="" set "PORT=%~1"
set "APPROOT=%CD%"
set "VENV_DIR=%APPROOT%\.venv"

REM ===== find Python (prefer py launcher) =====
where py >nul 2>&1 && (set "PYLAUNCH=py -3") || (set "PYLAUNCH=python")

REM ===== ensure venv =====
if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [info] creating venv in %VENV_DIR% ...
  %PYLAUNCH% -m venv "%VENV_DIR%" || (echo [FATAL] could not create venv & pause & exit /b 1)
)

call "%VENV_DIR%\Scripts\activate" || (echo [FATAL] failed to activate venv & pause & exit /b 1)

REM ===== deps: prefer extras\requirements.txt, then requirements.txt, else just Streamlit =====
set "REQ=%APPROOT%\extras\requirements.txt"
if not exist "%REQ%" set "REQ=%APPROOT%\requirements.txt"

python -m pip install -U pip wheel
if exist "%REQ%" (
  echo [info] installing from %REQ% ...
  python -m pip install -r "%REQ%" || (echo [ERROR] pip install failed & pause & exit /b 1)
) else (
  python -m pip show streamlit >nul 2>&1 || (python -m pip install -U streamlit) || (echo [ERROR] streamlit install failed & pause & exit /b 1)
)

REM ===== pick entry: program\app_main.py or programs\app_main.py =====
set "ENTRY_REL=program\app_main.py"
if not exist "%APPROOT%\%ENTRY_REL%" set "ENTRY_REL=programs\app_main.py"
set "ENTRY=%APPROOT%\%ENTRY_REL%"
if not exist "%ENTRY%" (
  echo [FATAL] App entry not found: %ENTRY%
  pause & exit /b 1
)

echo Starting BreakoutBuddy on http://127.0.0.1:%PORT% using %ENTRY_REL%
python -m streamlit run "%ENTRY%" --server.address 127.0.0.1 --server.port %PORT% --server.headless false
if errorlevel 1 (
  echo [ERROR] streamlit exited with %errorlevel%
  pause
)

popd
endlocal
