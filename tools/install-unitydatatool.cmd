@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "VERSION=2.2.0"
set "DEST=%CD%\.tools\UnityDataTool\v%VERSION%"
set "EXE=%DEST%\UnityDataTool.exe"
set "EXPECTED_SHA256=0454a2c9db06d15f33ceb2f5b0a9c305353fb225db8afae24fefbba7e7b68997"
set "URL=https://github.com/Unity-Technologies/UnityDataTools/releases/download/v%VERSION%/v%VERSION%-UnityDataTool-windows-x64-release.zip"

if exist "%EXE%" (
    "%EXE%" --version
    exit /b %ERRORLEVEL%
)

echo === Installing UnityDataTool v%VERSION% locally ===
echo Destination: %DEST%
echo.

where powershell.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: powershell.exe is required to unpack the official UnityDataTool release.
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$ProgressPreference='SilentlyContinue';" ^
  "$zip=Join-Path $env:TEMP 'UnityDataTool-v%VERSION%-windows-x64.zip';" ^
  "Invoke-WebRequest '%URL%' -OutFile $zip;" ^
  "$actual=(Get-FileHash -Algorithm SHA256 $zip).Hash.ToLowerInvariant();" ^
  "if ($actual -ne '%EXPECTED_SHA256%') { throw \"UnityDataTool SHA256 mismatch: $actual\" };" ^
  "if (Test-Path '%DEST%') { Remove-Item -Recurse -Force '%DEST%' };" ^
  "New-Item -ItemType Directory -Force -Path '%DEST%' | Out-Null;" ^
  "Expand-Archive -Path $zip -DestinationPath '%DEST%' -Force;"

if errorlevel 1 exit /b 1

if not exist "%EXE%" (
    echo ERROR: UnityDataTool.exe was not found after extraction.
    exit /b 1
)

"%EXE%" --version
endlocal
