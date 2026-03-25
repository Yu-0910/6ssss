@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Phase 2: パース実行中...
python scripts\parse_yahoo_game_pilot.py
echo.
echo 正規化実行中...
python scripts\normalize_plate_appearances.py
echo.
pause
