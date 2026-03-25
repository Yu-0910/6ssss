@echo off
chcp 65001 >nul
cd /d "%~dp0"
python scripts\parse_yahoo_game_pilot.py
pause
