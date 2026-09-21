@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"

set "MANAGED=%GAME_ROOT%\Shape of Dreams_Data\Managed"
set "ASSEMBLY=%MANAGED%\Dew.Contents.dll"
set "OUT=%CD%\data\extracted\managed-metadata"
set "TRACE=%OUT%\big-chomp-achievement-attributes.txt"

echo === Shape of Dreams Big Chomp metadata trace ===
echo Game: %GAME_ROOT%
echo Assembly: %ASSEMBLY%
echo.

where dotnet >nul 2>&1
if errorlevel 1 (
    echo ERROR: dotnet is not available on PATH.
    exit /b 1
)

if not exist "%ASSEMBLY%" (
    echo ERROR: Missing "%ASSEMBLY%"
    exit /b 1
)

if not exist "%OUT%" mkdir "%OUT%"

echo [1/2] Building metadata scanner...
dotnet build "%CD%\tools\MetadataTrace\MetadataTrace.csproj" -c Release --nologo
if errorlevel 1 exit /b 1

echo [2/2] Scanning AchUnlockOnComplete attributes for St_U_BigChomp...
dotnet run --project "%CD%\tools\MetadataTrace\MetadataTrace.csproj" -c Release --no-build -- "%ASSEMBLY%" "St_U_BigChomp" "AchUnlockOnComplete" > "%TRACE%"
set "SCAN_EXIT=%ERRORLEVEL%"

type "%TRACE%"
echo.
echo Trace: %TRACE%

if "%SCAN_EXIT%"=="0" (
    echo.
    echo RESULT: At least one achievement unlock attribute targets St_U_BigChomp.
    exit /b 0
)

if "%SCAN_EXIT%"=="1" (
    echo.
    echo RESULT: No AchUnlockOnComplete attribute targeting St_U_BigChomp was found in Dew.Contents.dll.
    exit /b 0
)

exit /b %SCAN_EXIT%
