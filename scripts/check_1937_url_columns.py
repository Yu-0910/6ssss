#!/usr/bin/env python3
"""1937年データのURL列を確認"""
from pathlib import Path
import csv

backup_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting\data\batting\backups\20251222_014659\yearly_from_master\batting_1937_PRE_from_master.csv")

with open(backup_path, encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    data = list(reader)

print(f"全行数: {len(data)}行")
print(f"\n列名:")
for i, col in enumerate(data[0].keys(), 1):
    print(f"  {i}. {col}")

print(f"\nURL関連の列:")
url_cols = [col for col in data[0].keys() if 'url' in col.lower() or 'source' in col.lower() or 'page' in col.lower()]
if url_cols:
    for col in url_cols:
        print(f"  - {col}")
        # サンプル値を表示
        sample_values = [row[col] for row in data[:5] if row.get(col)]
        if sample_values:
            print(f"    サンプル: {sample_values[0][:100] if len(sample_values[0]) > 100 else sample_values[0]}")
else:
    print("  URL関連の列が見つかりませんでした")

print(f"\n最初の5行のデータ（player_id, year, 主要列）:")
for i, row in enumerate(data[:5], 1):
    print(f"\n  行{i}:")
    print(f"    player_id: {row.get('player_id', 'N/A')}")
    print(f"    year: {row.get('year', 'N/A')}")
    print(f"    player_name_ja: {row.get('player_name_ja', 'N/A')}")
    if url_cols:
        for col in url_cols:
            val = row.get(col, '')
            if val:
                print(f"    {col}: {val[:100] if len(val) > 100 else val}")





















