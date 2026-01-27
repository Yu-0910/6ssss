#!/usr/bin/env python3
"""9行ある選手の詳細を確認"""
from pathlib import Path
import csv
from collections import defaultdict

base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")

# バックアップファイル
backup_path = base_path / "data" / "batting" / "backups" / "20251222_014659" / "yearly_from_master" / "batting_1937_PRE_from_master.csv"

# 現在の分割データ
current_spring_path = base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_spring_PRE.csv"
current_fall_path = base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_fall_PRE.csv"

# jbl参照データ
jbl_spring_path = base_path / "data" / "batting" / "jbl" / "batting_1937S_from_individual.csv"
jbl_fall_path = base_path / "data" / "batting" / "jbl" / "batting_1937A_from_individual.csv"

print("=" * 80)
print("9行ある選手の詳細調査")
print("=" * 80)

# バックアップデータを読み込む
with open(backup_path, encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    backup_data = list(reader)

# 1937年のデータをフィルタ
backup_1937_data = [row for row in backup_data if '1937' in str(row.get('year', '')).strip()]

# player_id + yearでグループ化
key_to_rows = defaultdict(list)
for row in backup_1937_data:
    player_id = str(row.get('player_id', '')).strip()
    year_val = str(row.get('year', '')).strip()
    key = (player_id, year_val)
    key_to_rows[key].append(row)

# 9行のキーを探す
nine_row_keys = [(key, rows) for key, rows in key_to_rows.items() if len(rows) == 9]

print(f"\n9行あるキー: {len(nine_row_keys)}個")

if nine_row_keys:
    player_id, year_val = nine_row_keys[0][0]
    rows = nine_row_keys[0][1]
    
    print(f"\nplayer_id: {player_id}")
    print(f"year: {year_val}")
    print(f"行数: {len(rows)}行")
    
    # 選手名を表示
    if rows:
        player_name = rows[0].get('player_name_ja', 'N/A')
        print(f"選手名: {player_name}")
    
    # 各行の詳細を表示
    print(f"\n[各行の詳細]")
    for i, row in enumerate(rows, 1):
        print(f"\n  行{i}:")
        print(f"    G (試合): {row.get('G', 'N/A')}")
        print(f"    PA (打席): {row.get('PA', 'N/A')}")
        print(f"    AB (打数): {row.get('AB', 'N/A')}")
        print(f"    H (安打): {row.get('H', 'N/A')}")
        print(f"    HR (本塁打): {row.get('HR', 'N/A')}")
        print(f"    RBI (打点): {row.get('RBI', 'N/A')}")
        print(f"    team (チーム): {row.get('team', 'N/A')}")
    
    # 統計データのパターンを分析
    print(f"\n[統計データのパターン分析]")
    stats_patterns = defaultdict(list)
    for i, row in enumerate(rows):
        stats_key = (row.get('G'), row.get('PA'), row.get('AB'), row.get('H'), row.get('HR'))
        stats_patterns[stats_key].append(i + 1)
    
    print(f"  ユニークな統計パターン数: {len(stats_patterns)}")
    for pattern, row_nums in stats_patterns.items():
        print(f"    パターン（G={pattern[0]}, PA={pattern[1]}, AB={pattern[2]}, H={pattern[3]}, HR={pattern[4]}）")
        print(f"      出現行: {row_nums}（{len(row_nums)}回）")
    
    # 現在の分割データでの状態
    print(f"\n[現在の分割データでの状態]")
    
    if current_spring_path.exists():
        with open(current_spring_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            spring_data = list(reader)
        
        spring_rows_for_player = [row for row in spring_data if str(row.get('player_id', '')).strip() == player_id]
        print(f"  春: {len(spring_rows_for_player)}行")
        for i, row in enumerate(spring_rows_for_player, 1):
            print(f"    行{i}: G={row.get('G')}, PA={row.get('PA')}, AB={row.get('AB')}, H={row.get('H')}")
    
    if current_fall_path.exists():
        with open(current_fall_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fall_data = list(reader)
        
        fall_rows_for_player = [row for row in fall_data if str(row.get('player_id', '')).strip() == player_id]
        print(f"  秋: {len(fall_rows_for_player)}行")
        for i, row in enumerate(fall_rows_for_player, 1):
            print(f"    行{i}: G={row.get('G')}, PA={row.get('PA')}, AB={row.get('AB')}, H={row.get('H')}")
    
    # jbl参照データでの状態
    print(f"\n[jbl参照データでの状態]")
    
    if jbl_spring_path.exists():
        with open(jbl_spring_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            jbl_spring_data = list(reader)
        
        jbl_spring_rows = [row for row in jbl_spring_data if str(row.get('player_id', '')).strip() == player_id]
        print(f"  jbl春: {len(jbl_spring_rows)}行")
        for i, row in enumerate(jbl_spring_rows, 1):
            print(f"    行{i}: G={row.get('G')}, PA={row.get('PA')}, AB={row.get('AB')}, H={row.get('H')}")
    
    if jbl_fall_path.exists():
        with open(jbl_fall_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            jbl_fall_data = list(reader)
        
        jbl_fall_rows = [row for row in jbl_fall_data if str(row.get('player_id', '')).strip() == player_id]
        print(f"  jbl秋: {len(jbl_fall_rows)}行")
        for i, row in enumerate(jbl_fall_rows, 1):
            print(f"    行{i}: G={row.get('G')}, PA={row.get('PA')}, AB={row.get('AB')}, H={row.get('H')}")
    
    # 分析と推奨事項
    print(f"\n[分析]")
    if len(stats_patterns) == 2:
        print(f"  9行のデータは2種類の統計パターンが繰り返されている可能性が高い")
        print(f"  実際には春・秋の2行が正しいデータで、残りは重複の可能性")
    elif len(stats_patterns) == 1:
        print(f"  9行すべてが同じ統計データ（完全な重複）")
    else:
        print(f"  複数の異なる統計パターンが混在している可能性")

else:
    print("\n9行あるキーが見つかりませんでした。")





















