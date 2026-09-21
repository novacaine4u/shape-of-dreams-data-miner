@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === Shape of Dreams Data Miner - Windows Update ===
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not available on PATH.
    exit /b 1
)

for /f "delims=" %%I in ('git rev-parse --show-toplevel 2^>nul') do set "REPO_ROOT=%%I"
if not defined REPO_ROOT (
    echo ERROR: This script is not inside a Git checkout.
    exit /b 1
)

cd /d "%REPO_ROOT%"

for /f "delims=" %%I in ('git branch --show-current') do set "CURRENT_BRANCH=%%I"
if /I not "%CURRENT_BRANCH%"=="main" (
    echo ERROR: Expected branch main, but current branch is "%CURRENT_BRANCH%".
    echo Switch to main before running this updater.
    exit /b 1
)

for /f "delims=" %%I in ('git status --porcelain') do set "DIRTY=1"
if defined DIRTY (
    echo ERROR: Working tree has local changes.
    echo Commit, stash, or discard them before updating.
    git status --short
    exit /b 1
)

echo [1/5] Fetching latest repository state...
git fetch origin --prune
if errorlevel 1 exit /b 1

echo [2/5] Fast-forwarding main...
git pull --ff-only origin main
if errorlevel 1 exit /b 1

if not exist ".venv\Scripts\python.exe" (
    echo [3/5] Creating Python 3.12 virtual environment...
    where py >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python launcher "py" is not available.
        exit /b 1
    )
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo ERROR: Could not create .venv with Python 3.12.
        echo Install Python 3.12 x64 and try again.
        exit /b 1
    )
) else (
    echo [3/5] Existing virtual environment found.
)

set "PY=%REPO_ROOT%\.venv\Scripts\python.exe"

echo [4/5] Installing current checkout into the virtual environment...
"%PY%" -m pip install -e .
if errorlevel 1 exit /b 1

echo [5/5] Running tests...
"%PY%" -m unittest discover -s tests -v
if errorlevel 1 (
    echo.
    echo ERROR: Update downloaded, but tests failed.
    exit /b 1
)

echo.
echo === Update complete ===
git log -1 --oneline
echo Python:
"%PY%" --version
echo.
echo Run the miner with:
echo   .venv\Scripts\sodminer.exe --help

endlocal
