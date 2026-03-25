@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Phase 1-b: 2023→1950 投手成績スクレイピングを開始します。
echo 進捗は [N/148] と _data\master_csv__import_1950_2024\phase1b_progress.log で確認できます。
echo.
python scripts\scrape_npb_pitching_stats.py --year 2023 --batch-to 1950
echo.
echo 終了しました。エラーがあれば上記を確認してください。
pause
