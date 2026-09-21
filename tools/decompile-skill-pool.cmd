@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"
set "MANAGED=%GAME_ROOT%\Shape of Dreams_Data\Managed"
set "CORE=%MANAGED%\Dew.Core.dll"
set "OUT=%CD%\data\extracted\skill-pool-decompiled"

echo === Shape of Dreams skill pool decompile ===
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

echo [1/4] Restoring repo-local ILSpy command...
dotnet tool restore --configfile "%CD%\NuGet.config"
if errorlevel 1 exit /b 1

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%" >nul

echo [2/4] Decompiling LootManager...
dotnet tool run ilspycmd -t "LootManager" "%CORE%" > "%OUT%\LootManager.cs"
if errorlevel 1 exit /b 1

echo [3/4] Decompiling Dew...
dotnet tool run ilspycmd -t "Dew" "%CORE%" > "%OUT%\Dew.cs"
if errorlevel 1 exit /b 1

echo [4/4] Building focused trace...
(
  echo ===== LootManager pool construction =====
  findstr /i /n /c:"poolSkillsByRarity" /c:"excludeFromPool" /c:"IExcludeFromPool" /c:"rarity" /c:"allSkills" /c:"allHeroSkills" "%OUT%\LootManager.cs"
  echo.
  echo ===== Dew skill catalogs =====
  findstr /i /n /c:"allSkills" /c:"allHeroSkills" /c:"IsSkillIncludedInGame" /c:"SkillTrigger" /c:"GetLoadoutSkills" "%OUT%\Dew.cs"
) > "%OUT%\skill-pool-trace.txt"

type "%OUT%\skill-pool-trace.txt"

echo.
echo Upload:
echo   %OUT%\LootManager.cs
echo   %OUT%\Dew.cs
echo   %OUT%\skill-pool-trace.txt

endlocal
