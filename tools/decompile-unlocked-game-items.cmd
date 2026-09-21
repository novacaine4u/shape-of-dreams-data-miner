@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"
set "MANAGED=%GAME_ROOT%\Shape of Dreams_Data\Managed"
set "CORE=%MANAGED%\Dew.Core.dll"
set "OUT=%CD%\data\extracted\unlocked-items-decompiled"

echo === Shape of Dreams unlocked game items decompile ===
echo Game: %GAME_ROOT%
echo.

where dotnet >nul 2>&1
if errorlevel 1 (
  echo ERROR: dotnet is not available on PATH.
  exit /b 1
)

if not exist "%CORE%" (
  echo ERROR: Missing "%CORE%"
  exit /b 1
)

echo [1/3] Restoring repo-local ILSpy command...
dotnet tool restore --configfile "%CD%\NuGet.config"
if errorlevel 1 exit /b 1

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%" >nul

echo [2/3] Decompiling DewPlayer...
dotnet tool run ilspycmd -t "DewPlayer" "%CORE%" > "%OUT%\DewPlayer.cs"
if errorlevel 1 exit /b 1

echo [3/3] Building focused trace...
(
  findstr /i /n /c:"unlockedGameItems" /c:"GetLocalUnlockedGameItems" /c:"UnlockStatus" /c:"NotDiscovered" /c:"isAvailableInGame" /c:"profileMain.skills" "%OUT%\DewPlayer.cs"
) > "%OUT%\unlocked-game-items-trace.txt"

type "%OUT%\unlocked-game-items-trace.txt"

echo.
echo Upload:
echo   %OUT%\DewPlayer.cs
echo   %OUT%\unlocked-game-items-trace.txt

endlocal
