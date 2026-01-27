#!/usr/bin/env python3
"""
同じ年度・同じリーグに同じ名前の選手が複数存在する場合を検出
"""

import csv
import os
from pathlib import Path
from collections import defaultdict

def find_duplicates_in_csv(csv_path: str):
    """CSVファイル内で同じ名前の選手を検出"""
    duplicates = defaultdict(list)
    
    if not os.path.exists(csv_path):
        return duplicates
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name_ja = row.get('player_name_ja', '').strip()
            if name_ja:
                player_id = row.get('player_id', '')
                team = row.get('team', '')
                games = row.get('G', '0')
                duplicates[name_ja].append({
                    'player_id': player_id,
                    'team': team,
                    'games': games,
                    'row': row
                })
    
    # 2人以上いる名前のみを返す
    return {name: entries for name, entries in duplicates.items() if len(entries) > 1}

def scan_all_csvs():
    """すべてのCSVファイルをスキャンして重複を検出"""
    project_root = Path(__file__).parent.parent
    csv_dirs = [
        project_root / '_data' / 'master_csv_calculated',
        project_root / '_data' / 'master_csv',
        project_root / '_data' / 'master_csv__import_1950_2024',
    ]
    
    all_duplicates = {}
    
    for csv_dir in csv_dirs:
        if not csv_dir.exists():
            continue
        
        for csv_file in csv_dir.glob('batting_*_*_from_master.csv'):
            duplicates = find_duplicates_in_csv(str(csv_file))
            if duplicates:
                all_duplicates[str(csv_file)] = duplicates
    
    return all_duplicates

def main():
    print("重複選手名を検索中...\n")
    
    all_duplicates = scan_all_csvs()
    
    if not all_duplicates:
        print("重複している選手名は見つかりませんでした。")
        return
    
    for csv_path, duplicates in all_duplicates.items():
        print(f"\n=== {csv_path} ===")
        for name, entries in duplicates.items():
            print(f"\n【{name}】 ({len(entries)}人)")
            for i, entry in enumerate(entries, 1):
                print(f"  {i}. player_id: {entry['player_id']}, チーム: {entry['team']}, 試合数: {entry['games']}")

if __name__ == '__main__':
    main()
