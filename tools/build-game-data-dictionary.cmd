@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"
set "RELEASE=%~2"
if not defined RELEASE set "RELEASE=v1.4.0"

set "UDT=%CD%\.tools\UnityDataTool\v2.2.0\UnityDataTool.exe"
set "BUNDLES=%GAME_ROOT%\Shape of Dreams_Data\StreamingAssets\aa\StandaloneWindows64"
set "RAWDATA=%GAME_ROOT%\RawData"
set "ANALYSIS=%CD%\data\extracted\%RELEASE%-addressables-analysis.db"
set "CACHE=%CD%\data\extracted\%RELEASE%-catalog-bundle-cache"
set "OUTPUT=%CD%\data\normalized\shape-of-dreams-%RELEASE%.sqlite"
set "SODMINER=%CD%\.venv\Scripts\sodminer.exe"
set "PYTHON=%CD%\.venv\Scripts\python.exe"

echo === Shape of Dreams game-wide data dictionary ===
echo Game: %GAME_ROOT%
echo Release: %RELEASE%
echo Output: %OUTPUT%
echo.

if exist "%UDT%" goto :udt_ready
call tools\install-unitydatatool.cmd
if errorlevel 1 exit /b 1
:udt_ready

if exist "%SODMINER%" goto :sodminer_ready
echo ERROR: sodminer virtual environment command is missing.
echo Run update-windows.cmd first.
exit /b 1
:sodminer_ready

if exist "%BUNDLES%" goto :bundles_ready
echo ERROR: Addressables bundle directory not found:
echo   %BUNDLES%
exit /b 1
:bundles_ready

if exist "%RAWDATA%" goto :rawdata_ready
echo ERROR: RawData directory not found:
echo   %RAWDATA%
exit /b 1
:rawdata_ready

if not exist "%CD%\data\extracted" mkdir "%CD%\data\extracted"
if not exist "%CD%\data\normalized" mkdir "%CD%\data\normalized"

echo [1/3] Analyzing all Addressables bundles...
"%UDT%" analyze "%BUNDLES%" -o "%ANALYSIS%" -p "*.bundle" --skip-crc
if errorlevel 1 exit /b 1

echo.
echo [2/3] Building normalized SQLite dictionary...
"%SODMINER%" catalog-build ^
  --analysis-db "%ANALYSIS%" ^
  --bundle-root "%BUNDLES%" ^
  --rawdata "%RAWDATA%" ^
  --unity-tool "%UDT%" ^
  --release "%RELEASE%" ^
  --source-root "%GAME_ROOT%" ^
  --cache-root "%CACHE%" ^
  --output "%OUTPUT%"
if errorlevel 1 exit /b 1

echo.
echo [3/3] Printing validation summary...
"%PYTHON%" tools\print-dictionary-summary.py "%OUTPUT%"
if errorlevel 1 exit /b 1

echo.
echo Complete.
echo SQLite dictionary:
echo   %OUTPUT%

endlocal
