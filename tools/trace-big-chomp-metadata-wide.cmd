@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"

set "MANAGED=%GAME_ROOT%\Shape of Dreams_Data\Managed"
set "CONTENTS=%MANAGED%\Dew.Contents.dll"
set "CORE=%MANAGED%\Dew.Core.dll"
set "OUT=%CD%\data\extracted\managed-metadata"
set "TRACE=%OUT%\big-chomp-wide-metadata.txt"

echo === Shape of Dreams Big Chomp wide metadata trace ===
echo Game: %GAME_ROOT%
echo.

where dotnet >nul 2>&1
if errorlevel 1 (
    echo ERROR: dotnet is not available on PATH.
    exit /b 1
)

if not exist "%CONTENTS%" (
    echo ERROR: Missing "%CONTENTS%"
    exit /b 1
)

if not exist "%CORE%" (
    echo ERROR: Missing "%CORE%"
    exit /b 1
)

if not exist "%OUT%" mkdir "%OUT%"

echo [1/3] Building metadata scanner...
dotnet build "%CD%\tools\MetadataTrace\MetadataTrace.csproj" -c Release --nologo
if errorlevel 1 exit /b 1

echo [2/3] Scanning Dew.Contents.dll...
(
  echo ===== Dew.Contents.dll =====
  dotnet run --project "%CD%\tools\MetadataTrace\MetadataTrace.csproj" -c Release --no-build -- "%CONTENTS%" "St_U_BigChomp" "*" "--matching-only"
) > "%TRACE%"
set "CONTENTS_EXIT=%ERRORLEVEL%"

echo [3/3] Scanning Dew.Core.dll...
(
  echo.
  echo ===== Dew.Core.dll =====
  dotnet run --project "%CD%\tools\MetadataTrace\MetadataTrace.csproj" -c Release --no-build -- "%CORE%" "St_U_BigChomp" "*" "--matching-only"
) >> "%TRACE%"
set "CORE_EXIT=%ERRORLEVEL%"

type "%TRACE%"
echo.
echo Trace: %TRACE%
echo.
echo Note: exit code 1 from an individual scan only means no matching custom attribute blob was found.

endlocal
