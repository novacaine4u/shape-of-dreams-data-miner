@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"

set "MANAGED=%GAME_ROOT%\Shape of Dreams_Data\Managed"
set "CORE=%MANAGED%\Dew.Core.dll"
set "CONTENTS=%MANAGED%\Dew.Contents.dll"
set "OUT=%CD%\data\extracted\discover-skill-callers-decompiled"

echo === Shape of Dreams DiscoverSkill caller decompile ===
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

if not exist "%CONTENTS%" (
    echo ERROR: Missing "%CONTENTS%"
    exit /b 1
)

echo [1/5] Restoring repo-local ILSpy command...
dotnet tool restore --configfile "%CD%\NuGet.config"
if errorlevel 1 exit /b 1

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%" >nul

echo [2/5] Decompiling AchievementManager...
dotnet tool run ilspycmd -t "AchievementManager" "%CORE%" > "%OUT%\AchievementManager.cs"
if errorlevel 1 exit /b 1

echo [3/5] Decompiling DewSave...
dotnet tool run ilspycmd -t "DewSave" "%CORE%" > "%OUT%\DewSave.cs"
if errorlevel 1 exit /b 1

echo [4/5] Decompiling Shrine_Ascension...
dotnet tool run ilspycmd -t "Shrine_Ascension" "%CONTENTS%" > "%OUT%\Shrine_Ascension.cs"
if errorlevel 1 exit /b 1

echo [5/5] Building focused trace...
(
    echo ===== AchievementManager DiscoverSkill context =====
    findstr /i /n /c:"DiscoverSkill" /c:"Dismantled" /c:"ClientHeroEventOnSkillPickup" "%OUT%\AchievementManager.cs"
    echo.
    echo ===== DewSave DiscoverSkill context =====
    findstr /i /n /c:"DiscoverSkill" /c:"CreateProfile" "%OUT%\DewSave.cs"
    echo.
    echo ===== Shrine_Ascension DiscoverSkill context =====
    findstr /i /n /c:"DiscoverSkill" /c:"RpcShowNotice" /c:"BigChomp" /c:"St_U_BigChomp" /c:"Ascension" "%OUT%\Shrine_Ascension.cs"
) > "%OUT%\discover-skill-caller-context.txt"

type "%OUT%\discover-skill-caller-context.txt"

echo.
echo Upload:
echo   %OUT%\AchievementManager.cs
echo   %OUT%\DewSave.cs
echo   %OUT%\Shrine_Ascension.cs
echo   %OUT%\discover-skill-caller-context.txt

endlocal
