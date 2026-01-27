#!/usr/bin/env python3
"""
同じ年度・同じリーグに同じ名前（または同じplayer_id）の選手が複数存在する場合、
片方を削除するスクリプト
"""

import csv
import os
from pathlib import Path
from collections import defaultdict

def find_and_remove_duplicates(csv_path: str):
    """CSVファイル内で重複している選手を検出し、片方を削除"""
    if not os.path.exists(csv_path):
        print(f"ファイルが見つかりません: {csv_path}")
        return False
    
    rows = []
    seen_names = {}  # 名前 -> 最初に見つかった行のインデックス
    seen_ids = {}    # player_id -> 最初に見つかった行のインデックス
    duplicates_to_remove = set()  # 削除する行のインデックス
    
    # CSVファイルを読み込む
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        for idx, row in enumerate(reader):
            rows.append(row)
            name_ja = row.get('player_name_ja', '').strip()
            player_id = row.get('player_id', '').strip()
            year = row.get('year', '').strip()
            league = row.get('league', '').strip()
            
            # 同じplayer_idが既に存在する場合（より厳密なチェック、優先）
            if player_id and player_id in seen_ids:
                existing_idx = seen_ids[player_id]
                # 同じplayer_idの場合は、後から見つかった方を削除（最初に見つかった方を保持）
                duplicates_to_remove.add(idx)
                print(f"削除（player_id重複）: {name_ja} (player_id: {player_id}, チーム: {row.get('team', '')}, 試合数: {row.get('G', '0')})")
            elif player_id:
                seen_ids[player_id] = idx
            
            # 同じ年度・同じリーグで同じ名前の選手が既に存在する場合（player_idが異なる場合）
            key = (year, league, name_ja)
            if name_ja and key in seen_names and player_id not in seen_ids:
                # 既存の行と比較して、試合数が少ない方を削除
                existing_idx = seen_names[key]
                existing_games = float(rows[existing_idx].get('G', '0') or '0')
                current_games = float(row.get('G', '0') or '0')
                
                if current_games < existing_games:
                    duplicates_to_remove.add(idx)
                    print(f"削除（名前重複）: {name_ja} (player_id: {player_id}, チーム: {row.get('team', '')}, 試合数: {current_games})")
                else:
                    duplicates_to_remove.add(existing_idx)
                    print(f"削除（名前重複）: {name_ja} (player_id: {rows[existing_idx].get('player_id', '')}, チーム: {rows[existing_idx].get('team', '')}, 試合数: {existing_games})")
                    seen_names[key] = idx
            elif name_ja and player_id not in seen_ids:
                seen_names[key] = idx
    
    # 重複を削除
    if duplicates_to_remove:
        filtered_rows = [row for idx, row in enumerate(rows) if idx not in duplicates_to_remove]
        
        # バックアップを作成
        backup_path = csv_path + '.backup'
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy2(csv_path, backup_path)
            print(f"バックアップを作成: {backup_path}")
        
        # CSVファイルを書き込む
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(filtered_rows)
        
        print(f"✅ {len(duplicates_to_remove)}件の重複を削除しました: {csv_path}")
        return True
    else:
        print(f"重複は見つかりませんでした: {csv_path}")
        return False

def main():
    # スクリプトのディレクトリから相対パスでプロジェクトルートを取得
    try:
        script_dir = Path(__file__).parent.resolve()
        project_root = script_dir.parent.resolve()
    except:
        # __file__が使えない場合は、現在の作業ディレクトリを使用
        project_root = Path(os.getcwd()).resolve()
        script_dir = project_root / 'scripts'
    
    print(f"プロジェクトルート: {project_root}")
    print(f"現在の作業ディレクトリ: {os.getcwd()}")
    
    csv_dirs = [
        project_root / '_data' / 'master_csv_calculated',
        project_root / '_data' / 'master_csv',
        project_root / '_data' / 'master_csv__import_1950_2024',
    ]
    
    total_removed = 0
    
    for csv_dir in csv_dirs:
        if not csv_dir.exists():
            print(f"ディレクトリが存在しません: {csv_dir}")
            continue
        
        print(f"\nスキャン中: {csv_dir}")
        for csv_file in sorted(csv_dir.glob('batting_*_*_from_master.csv')):
            print(f"\n処理中: {csv_file.name}")
            if find_and_remove_duplicates(str(csv_file)):
                total_removed += 1
    
    print(f"\n✅ 処理完了。{total_removed}個のファイルで重複を削除しました。")

if __name__ == '__main__':
    main()
