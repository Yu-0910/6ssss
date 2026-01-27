#!/usr/bin/env python3
"""残っている重複の年度・リーグを確認"""
import csv
from pathlib import Path

script_dir = Path(__file__).parent.resolve()
project_root = script_dir.parent.resolve()
csv_path = project_root / 'output' / 'reports' / 'duplicate_player_names_in_rankings.csv'

with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    years_leagues = set((row['year'], row['league']) for row in reader)

print('残っている年度・リーグ:')
for yl in sorted(years_leagues):
    print(f'  {yl[0]} {yl[1]}')
print(f'\n合計: {len(years_leagues)} 組')
