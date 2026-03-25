@echo off
chcp 65001 >nul
cd /d "%~dp0"
set LOGFILE=phase1b_2000_2003_progress.log
set LOGPATH=_data\master_csv__import_1950_2024\%LOGFILE%
if exist "%LOGPATH%" type nul > "%LOGPATH%"
echo Phase 1-b 2004年形式: 2003→2000 を「全ての選手から探す」経由で実行します。
echo 1年度あたり十数分かかります。
echo 進捗: この窓の表示のほか、%LOGPATH% をCursorで開き「更新」で追記を確認できます。
echo.
for %%Y in (2003 2002 2001 2000) do (
  echo ========== %%Y 年 ==========
  python scripts\scrape_2004_pitching_via_all_players.py --year %%Y --progress-log %LOGFILE%
  if errorlevel 1 (
    echo %%Y 年でエラーが発生しました。
    pause
    exit /b 1
  )
  echo.
)
echo 2003〜2000 の取得が完了しました。
pause
