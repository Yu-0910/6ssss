@echo off
chcp 65001 >nul
cd /d "%~dp0.."
python scripts/fetch_pitcher_zone_stats.py --game-id 2021040084 --pitcher-id 2103788 --out-dir _data/yahoo_games_pilot
echo.
pause
