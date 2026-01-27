# -*- coding: utf-8 -*-
import csv
import os
from pathlib import Path

def remove_duplicates(csv_path):
    """CSVファイルから重複している選手を削除"""
    if not os.path.exists(csv_path):
        print(f"ファイルが見つかりません: {csv_path}")
        return False
    
    rows = []
    seen_ids = {}
    duplicates_to_remove = set()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        for idx, row in enumerate(reader):
            rows.append(row)
            player_id = row.get('player_id', '').strip()
            name_ja = row.get('player_name_ja', '').strip()
            year = row.get('year', '').strip()
            league = row.get('league', '').strip()
            
            # 同じplayer_idが既に存在する場合
            if player_id and player_id in seen_ids:
                duplicates_to_remove.add(idx)
                print(f"削除: {name_ja} (player_id: {player_id}, チーム: {row.get('team', '')})")
            elif player_id:
                seen_ids[player_id] = idx
    
    if duplicates_to_remove:
        filtered_rows = [row for idx, row in enumerate(rows) if idx not in duplicates_to_remove]
        
        # バックアップ
        backup_path = csv_path + '.backup'
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy2(csv_path, backup_path)
            print(f"バックアップ作成: {backup_path}")
        
        # 書き込み
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(filtered_rows)
        
        print(f"✅ {len(duplicates_to_remove)}件削除: {os.path.basename(csv_path)}")
        return True
    return False

# 直接実行
if __name__ == '__main__':
    base = Path('_data/master_csv_calculated')
    if base.exists():
        for f in sorted(base.glob('batting_*_*_from_master.csv')):
            remove_duplicates(str(f))
    else:
        print(f"ディレクトリが見つかりません: {base}")
