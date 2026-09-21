@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"
set "MANAGED=%GAME_ROOT%\Shape of Dreams_Data\Managed"
set "OUT=%CD%\data\extracted\managed-decompile"

echo === Shape of Dreams managed-code trace ===
echo Game: %GAME_ROOT%
echo.

where dotnet >nul 2>&1
if errorlevel 1 (
    echo ERROR: dotnet is not available on PATH.
    echo Install a .NET 8 or newer SDK/runtime, then rerun this command.
    exit /b 1
)

if not exist "%MANAGED%\Dew.Contents.dll" (
    echo ERROR: Missing "%MANAGED%\Dew.Contents.dll"
    exit /b 1
)

if not exist "%MANAGED%\Dew.Core.dll" (
    echo ERROR: Missing "%MANAGED%\Dew.Core.dll"
    exit /b 1
)

echo [1/4] Restoring repo-local ILSpy command...
dotnet tool restore --configfile "%CD%\NuGet.config"
if errorlevel 1 exit /b 1

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%\Dew.Contents" >nul
mkdir "%OUT%\Dew.Core" >nul

echo [2/4] Decompiling Dew.Contents.dll...
dotnet tool run ilspycmd -p -o "%OUT%\Dew.Contents" "%MANAGED%\Dew.Contents.dll"
if errorlevel 1 exit /b 1

echo [3/4] Decompiling Dew.Core.dll...
dotnet tool run ilspycmd -p -o "%OUT%\Dew.Core" "%MANAGED%\Dew.Core.dll"
if errorlevel 1 exit /b 1

echo [4/4] Searching decompiled source...
(
  echo === St_U_BigChomp ===
  findstr /s /i /n /c:"St_U_BigChomp" "%OUT%\Dew.Contents\*.cs" "%OUT%\Dew.Core\*.cs"
  echo.
  echo === AchUnlockOnComplete ===
  findstr /s /i /n /c:"AchUnlockOnComplete" "%OUT%\Dew.Contents\*.cs" "%OUT%\Dew.Core\*.cs"
) > "%OUT%\big-chomp-unlock-trace.txt"

type "%OUT%\big-chomp-unlock-trace.txt"

echo.
echo Output:
echo   %OUT%
echo   %OUT%\big-chomp-unlock-trace.txt

endlocal
