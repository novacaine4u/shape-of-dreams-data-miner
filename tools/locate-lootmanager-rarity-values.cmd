@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams"
set "DATA_ROOT=%GAME_ROOT%\Shape of Dreams_Data"
set "OUT=%CD%\data\extracted\lootmanager-locator"

echo === Shape of Dreams LootManager serialized-value locator ===
echo Game: %GAME_ROOT%
echo.

if not exist "%DATA_ROOT%" goto :missing_data
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%" >nul

echo [1/5] Locating LootManager...
sodminer strings "%DATA_ROOT%" --release v1.4.0 --contains "LootManager" --output "%OUT%\lootmanager.jsonl"
if errorlevel 1 exit /b 1

echo [2/5] Locating skillRarityChance...
sodminer strings "%DATA_ROOT%" --release v1.4.0 --contains "skillRarityChance" --output "%OUT%\skill-rarity-chance.jsonl"
if errorlevel 1 exit /b 1

echo [3/5] Locating skillRarityChanceHigh...
sodminer strings "%DATA_ROOT%" --release v1.4.0 --contains "skillRarityChanceHigh" --output "%OUT%\skill-rarity-chance-high.jsonl"
if errorlevel 1 exit /b 1

echo [4/5] Locating gemRarityChance...
sodminer strings "%DATA_ROOT%" --release v1.4.0 --contains "gemRarityChance" --output "%OUT%\gem-rarity-chance.jsonl"
if errorlevel 1 exit /b 1

echo [5/5] Locating gemRarityChanceHigh...
sodminer strings "%DATA_ROOT%" --release v1.4.0 --contains "gemRarityChanceHigh" --output "%OUT%\gem-rarity-chance-high.jsonl"
if errorlevel 1 exit /b 1

echo.
echo Upload these files:
echo   %OUT%\lootmanager.jsonl
echo   %OUT%\skill-rarity-chance.jsonl
echo   %OUT%\skill-rarity-chance-high.jsonl
echo   %OUT%\gem-rarity-chance.jsonl
echo   %OUT%\gem-rarity-chance-high.jsonl
exit /b 0

:missing_data
echo ERROR: Game data directory not found:
echo   %DATA_ROOT%
exit /b 1
