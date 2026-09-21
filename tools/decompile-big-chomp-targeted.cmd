@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"

set "MANAGED=%GAME_ROOT%\Shape of Dreams_Data\Managed"
set "CONTENTS=%MANAGED%\Dew.Contents.dll"
set "CORE=%MANAGED%\Dew.Core.dll"
set "OUT=%CD%\data\extracted\managed-targeted"

echo === Shape of Dreams targeted unlock decompile ===
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

echo [1/5] Restoring repo-local ILSpy command...
dotnet tool restore --configfile "%CD%\NuGet.config"
if errorlevel 1 exit /b 1

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%" >nul

echo [2/5] Decompiling St_U_BigChomp...
dotnet tool run ilspycmd -t "St_U_BigChomp" "%CONTENTS%" > "%OUT%\St_U_BigChomp.cs"
if errorlevel 1 (
    echo ERROR: Could not decompile St_U_BigChomp.
    exit /b 1
)

echo [3/5] Decompiling SkillTrigger...
dotnet tool run ilspycmd -t "SkillTrigger" "%CORE%" > "%OUT%\SkillTrigger.cs"
if errorlevel 1 (
    echo WARNING: SkillTrigger was not decompiled from Dew.Core.dll.
    echo Trying Dew.Contents.dll...
    dotnet tool run ilspycmd -t "SkillTrigger" "%CONTENTS%" > "%OUT%\SkillTrigger.cs"
    if errorlevel 1 (
        echo ERROR: Could not decompile SkillTrigger from either assembly.
        exit /b 1
    )
)

echo [4/5] Decompiling DewProfile...
dotnet tool run ilspycmd -t "DewProfile" "%CORE%" > "%OUT%\DewProfile.cs"
if errorlevel 1 (
    echo WARNING: DewProfile was not decompiled from Dew.Core.dll.
    echo Trying Dew.Contents.dll...
    dotnet tool run ilspycmd -t "DewProfile" "%CONTENTS%" > "%OUT%\DewProfile.cs"
    if errorlevel 1 (
        echo ERROR: Could not decompile DewProfile from either assembly.
        exit /b 1
    )
)

echo [5/5] Building focused trace...
(
    echo ===== St_U_BigChomp.cs =====
    type "%OUT%\St_U_BigChomp.cs"
    echo.
    echo ===== Unlock/profile search =====
    findstr /i /n /c:"St_U_BigChomp" /c:"UnlockStatus" /c:"NotDiscovered" /c:"Locked" /c:"UnlockData" /c:"skills" /c:"Hero" /c:"Achievement" "%OUT%\SkillTrigger.cs" "%OUT%\DewProfile.cs"
) > "%OUT%\big-chomp-targeted-unlock-trace.txt"

type "%OUT%\big-chomp-targeted-unlock-trace.txt"

echo.
echo Output directory:
echo   %OUT%
echo.
echo Upload:
echo   %OUT%\St_U_BigChomp.cs
echo   %OUT%\SkillTrigger.cs
echo   %OUT%\DewProfile.cs
echo   %OUT%\big-chomp-targeted-unlock-trace.txt

endlocal
