@echo off
REM BreakoutBuddy launcher (no hardcoded folder names)
REM Place this file INSIDE your app folder (the one that contains 'program' and 'Data').

setlocal enabledelayedexpansion

REM APP_DIR = folder containing this .bat
set "APP_DIR=%~dp0"
REM Strip trailing backslash
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

set "BREAKOUTBUDDY_DATA=%APP_DIR%\Data"
echo Using BREAKOUTBUDDY_DATA=%BREAKOUTBUDDY_DATA%

REM Optional: persist across sessions
REM setx BREAKOUTBUDDY_DATA "%BREAKOUTBUDDY_DATA%" >nul

cd /d "%APP_DIR%"
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

python -c "import os;print('Data->', os.environ.get('BREAKOUTBUDDY_DATA','<unset>'))"
streamlit run program/app_main.py
