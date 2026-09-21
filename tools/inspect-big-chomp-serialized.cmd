@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"
set "UDT=%CD%\.tools\UnityDataTool\v2.2.0\UnityDataTool.exe"

echo === Shape of Dreams Big Chomp serialized inspection ===
echo Game: %GAME_ROOT%
echo.

if not exist "%UDT%" (
    call tools\install-unitydatatool.cmd
    if errorlevel 1 exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Repo Python virtual environment is missing.
    echo Run update-windows.cmd first.
    exit /b 1
)

".venv\Scripts\python.exe" tools\inspect_big_chomp_serialized.py ^
  --game-root "%GAME_ROOT%" ^
  --tool "%UDT%" ^
  --output "data\extracted\big-chomp-serialized"

if errorlevel 1 exit /b 1

echo.
echo Upload:
echo   data\extracted\big-chomp-serialized\summary.txt

endlocal
