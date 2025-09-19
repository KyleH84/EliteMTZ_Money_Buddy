@echo off
title ==== AstroLotto Launcher (Windows) ====
echo.

cd /d "%~dp0"

REM --- Try Python from PATH or py launcher ---
where python >nul 2>nul
if %errorlevel%==0 (
    set "PYEXE=python"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PYEXE=py -3"
    ) else (
        echo Could not find Python. Please install Python 3.10+ and add it to PATH.
        pause
        exit /b
    )
)

echo Using: %PYEXE%
echo.

echo Installing requirements...
%PYEXE% -m pip install --upgrade pip
if exist "Extras\requirements.txt" (
    %PYEXE% -m pip install -r Extras\requirements.txt
) else (
    %PYEXE% -m pip install streamlit pandas numpy
)

echo.
echo ==== Starting AstroLotto (V15) ====
cd programs
%PYEXE% -m streamlit run app_main.py

echo.
pause
