#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1950年〜2002年の投手成績を scrape_2004_pitching_via_all_players.py で一括取得する。

使用例:
  python scripts/run_pitching_scrape_1950_2002.py
  python scripts/run_pitching_scrape_1950_2002.py --from-year 1990 --to-year 2000
  python scripts/run_pitching_scrape_1950_2002.py --year 1955
"""
import argparse
import subprocess
import sys
from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='1950〜2002年投手成績を一括スクレイピング')
    parser.add_argument('--from-year', type=int, default=1950, help='開始年度（既定: 1950）')
    parser.add_argument('--to-year', type=int, default=2002, help='終了年度（既定: 2002）')
    parser.add_argument('--year', type=int, default=None, help='単年度のみ（指定時は from/to を無視）')
    parser.add_argument('--progress-log', type=str, default='pitching_scrape_1950_2002.log',
                        help='進捗ログファイル名（_data 配下）')
    parser.add_argument('--dry-run', action='store_true', help='実行せず対象年度のみ表示')
    args = parser.parse_args()

    if args.year is not None:
        years = [args.year]
    else:
        if args.from_year > args.to_year:
            print('エラー: --from-year は --to-year 以下にしてください')
            sys.exit(1)
        years = list(range(args.from_year, args.to_year + 1))

    script_dir = Path(__file__).resolve().parent
    scrape_script = script_dir / 'scrape_2004_pitching_via_all_players.py'

    if not scrape_script.exists():
        print(f'エラー: {scrape_script} が見つかりません')
        sys.exit(1)

    print(f'対象年度: {years[0]}年 〜 {years[-1]}年（{len(years)}年分）')
    if args.dry_run:
        print('--dry-run: 実行しません')
        for y in years:
            print(f'  {y}年')
        sys.exit(0)

    failed: list[int] = []
    for i, year in enumerate(years, 1):
        print(f'\n{"="*60}')
        print(f'[{i}/{len(years)}] {year}年')
        print('='*60)
        cmd = [
            sys.executable,
            str(scrape_script),
            '--year', str(year),
            '--progress-log', args.progress_log,
        ]
        ret = subprocess.run(cmd, cwd=script_dir.parent)
        if ret.returncode != 0:
            failed.append(year)
            print(f'⚠️ {year}年 失敗 (exit {ret.returncode})')
        else:
            print(f'✅ {year}年 完了')

    if failed:
        print(f'\n失敗した年度: {failed}')
        sys.exit(1)
    print('\n全年度 完了。')
