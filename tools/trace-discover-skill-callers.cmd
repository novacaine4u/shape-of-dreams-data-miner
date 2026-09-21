@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"

set "MANAGED=%GAME_ROOT%\Shape of Dreams_Data\Managed"
set "OUT=%CD%\data\extracted\managed-callers"
set "TRACE=%OUT%\discover-skill-callers.txt"

echo === Shape of Dreams DiscoverSkill caller trace ===
echo Game: %GAME_ROOT%
echo.

where dotnet >nul 2>&1
if errorlevel 1 (
    echo ERROR: dotnet is not available on PATH.
    exit /b 1
)

if not exist "%OUT%" mkdir "%OUT%"

echo [1/2] Building call-site tracer...
dotnet build "%CD%\tools\MethodCallTrace\MethodCallTrace.csproj" -c Release --nologo
if errorlevel 1 exit /b 1

echo [2/2] Scanning managed assemblies...
> "%TRACE%" echo ===== DewProfile.DiscoverSkill callers =====

for %%A in ("Dew.Core.dll" "Dew.Contents.dll" "Dew.UI.dll" "Assembly-CSharp.dll") do (
    if exist "%MANAGED%\%%~A" (
        >> "%TRACE%" echo.
        >> "%TRACE%" echo ===== %%~A =====
        dotnet run --project "%CD%\tools\MethodCallTrace\MethodCallTrace.csproj" -c Release --no-build -- "%MANAGED%\%%~A" "DewProfile" "DiscoverSkill" >> "%TRACE%"
    )
)

type "%TRACE%"

echo.
echo Trace:
echo   %TRACE%

endlocal
