#!/usr/bin/env python3
"""1937年の行数をデバッグ"""
from pathlib import Path
import csv
from collections import defaultdict

backup_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\backups\20251222_014659\yearly_from_master\batting_1937_PRE_from_master.csv")

with open(backup_path, encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    data = list(reader)

print(f"全行数: {len(data)}行")

# year列を確認
year_values = defaultdict(int)
for row in data:
    year_val = str(row.get('year', '')).strip()
    year_values[year_val] += 1

print(f"\nyear列の値:")
for year_val, count in sorted(year_values.items()):
    print(f"  '{year_val}': {count}行")

# 1937年でフィルタ
filtered = [row for row in data if '1937' in str(row.get('year', '')).strip()]
print(f"\n'1937'を含む行数: {len(filtered)}行")

# player_id + year でグループ化
key_to_rows = defaultdict(list)
for row in filtered:
    player_id = str(row.get('player_id', '')).strip()
    year_val = str(row.get('year', '')).strip()
    key = (player_id, year_val)
    key_to_rows[key].append(row)

print(f"\nplayer_id + year のユニークキー数: {len(key_to_rows)}")

# 重複を確認
duplicates = {k: rows for k, rows in key_to_rows.items() if len(rows) > 1}
singles = {k: rows for k, rows in key_to_rows.items() if len(rows) == 1}

print(f"  重複キー数（2行以上）: {len(duplicates)}")
print(f"  単一キー数（1行）: {len(singles)}")

total_from_duplicates = sum(len(rows) for rows in duplicates.values())
total_from_singles = sum(len(rows) for rows in singles.values())
print(f"  重複キーからの行数: {total_from_duplicates}行")
print(f"  単一キーからの行数: {total_from_singles}行")
print(f"  合計: {total_from_duplicates + total_from_singles}行")





















