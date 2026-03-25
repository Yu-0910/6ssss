@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Phase 1-b 計画書反映: 2022→2005 を実行します（球団別から全投手取得）。
echo 進捗: コンソールに [N/36] 表示、ログは _data\master_csv__import_1950_2024\phase1b_progress.log
echo.
python scripts\scrape_npb_pitching_stats.py --year 2022 --batch-to 2005
echo.
echo 終了しました。
pause
