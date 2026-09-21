@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"
set "DATA_ROOT=%GAME_ROOT%\Shape of Dreams_Data"
set "OUT=%CD%\data\extracted\big-chomp-resource"

echo === Shape of Dreams Big Chomp serialized-resource locator ===
echo Game: %GAME_ROOT%
echo.

if not exist "%DATA_ROOT%" (
  echo ERROR: Missing "%DATA_ROOT%"
  exit /b 1
)

if not exist "%OUT%" mkdir "%OUT%"

echo [1/2] Searching game data for St_U_BigChomp...
sodminer strings "%DATA_ROOT%" --release v1.4.0 --contains "St_U_BigChomp" --output "%OUT%\st-u-bigchomp-strings.jsonl"
if errorlevel 1 exit /b 1

echo [2/2] Searching game data for BigChomp...
sodminer strings "%DATA_ROOT%" --release v1.4.0 --contains "BigChomp" --output "%OUT%\bigchomp-strings.jsonl"
if errorlevel 1 exit /b 1

echo.
echo Upload:
echo   %OUT%\st-u-bigchomp-strings.jsonl
echo   %OUT%\bigchomp-strings.jsonl

endlocal
