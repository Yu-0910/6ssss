#!/usr/bin/env python3
"""
investigate_1937_split_issues.py

1937年の分割に関する問題を詳しく調査：
1. 秋シーズンの重複37人の原因
2. 春秋でデータ数に差がある原因
"""

import csv
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict


def load_csv_with_encoding(csv_path: Path) -> List[Dict[str, Any]]:
    """CSVファイルを読み込む（文字コード自動判定）"""
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                return list(reader)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    raise ValueError(f"Failed to read {csv_path} with any encoding")


def safe_int(value: Any, default: int = 0) -> int:
    """安全にintに変換"""
    if value is None or value == '':
        return default
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def create_player_stats_key(row: Dict[str, Any]) -> Tuple:
    """プレイヤーの統計からキーを生成"""
    key_fields = ['G', 'PA', 'AB', 'H', 'HR', 'RBI']
    key_values = []
    for field in key_fields:
        val = str(row.get(field, '')).strip()
        key_values.append(val if val else '0')
    return tuple(key_values)


def main():
    base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")
    
    # 現在の分割データ
    current_spring_path = base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_spring_PRE.csv"
    current_fall_path = base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_fall_PRE.csv"
    
    # バックアップファイル（元データ）
    backup_path = base_path / "data" / "batting" / "backups" / "20251222_014659" / "yearly_from_master" / "batting_1937_PRE_from_master.csv"
    
    print("=" * 80)
    print("1937年分割問題の調査")
    print("=" * 80)
    
    # データを読み込む
    print("\n[読み込み]")
    current_spring_data = load_csv_with_encoding(current_spring_path)
    current_fall_data = load_csv_with_encoding(current_fall_path)
    backup_data = load_csv_with_encoding(backup_path)
    backup_1937_data = [row for row in backup_data if '1937' in str(row.get('year', '')).strip()]
    
    print(f"  現在の春: {len(current_spring_data)}行")
    print(f"  現在の秋: {len(current_fall_data)}行")
    print(f"  バックアップ（1937年）: {len(backup_1937_data)}行")
    
    # 問題1: 秋シーズンの重複を調査
    print("\n" + "=" * 80)
    print("問題1: 秋シーズンの重複37人を調査")
    print("=" * 80)
    
    # 秋データのplayer_idをカウント
    fall_player_id_counts = defaultdict(list)
    for idx, row in enumerate(current_fall_data):
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            fall_player_id_counts[player_id].append((idx, row))
    
    fall_duplicates = {pid: rows for pid, rows in fall_player_id_counts.items() if len(rows) > 1}
    
    print(f"\n[秋シーズンの重複プレイヤー]")
    print(f"  重複プレイヤー数: {len(fall_duplicates)}人")
    print(f"  重複行数: {sum(len(rows) for rows in fall_duplicates.values())}行")
    
    if fall_duplicates:
        print(f"\n  重複プレイヤーの詳細（最初の10人）:")
        for i, (player_id, rows) in enumerate(list(fall_duplicates.items())[:10], 1):
            print(f"\n  {i}. player_id: {player_id}")
            print(f"     重複数: {len(rows)}行")
            for j, (idx, row) in enumerate(rows, 1):
                print(f"      行{j}: G={row.get('G')}, PA={row.get('PA')}, AB={row.get('AB')}, H={row.get('H')}, HR={row.get('HR')}")
    
    # バックアップデータでこれらのプレイヤーがどうなっているか確認
    print(f"\n[バックアップデータでの該当プレイヤーの状態]")
    backup_key_to_rows = defaultdict(list)
    for row in backup_1937_data:
        player_id = str(row.get('player_id', '')).strip()
        year_val = str(row.get('year', '')).strip()
        key = (player_id, year_val)
        backup_key_to_rows[key].append(row)
    
    duplicate_in_backup = {}
    for player_id in list(fall_duplicates.keys())[:10]:
        key = (player_id, '1937')
        if key in backup_key_to_rows:
            rows = backup_key_to_rows[key]
            duplicate_in_backup[player_id] = len(rows)
            print(f"  player_id {player_id}: バックアップでは{len(rows)}行")
    
    # 問題2: 春秋のデータ数の差を調査
    print("\n" + "=" * 80)
    print("問題2: 春秋でデータ数に差がある原因を調査")
    print("=" * 80)
    
    # バックアップデータでplayer_id + yearの重複パターンを分析
    print(f"\n[バックアップデータの重複パターン分析]")
    duplicate_patterns = defaultdict(int)
    for key, rows in backup_key_to_rows.items():
        pattern = len(rows)
        duplicate_patterns[pattern] += 1
    
    print(f"  重複パターンの分布:")
    for pattern in sorted(duplicate_patterns.keys()):
        count = duplicate_patterns[pattern]
        print(f"    {pattern}行のキー: {count}個")
    
    # 各パターンが春・秋にどう分割されたかを分析
    print(f"\n[各パターンの分割結果]")
    
    # 現在のデータからplayer_idを取得
    spring_player_ids = {str(row.get('player_id', '')).strip() for row in current_spring_data if str(row.get('player_id', '')).strip()}
    fall_player_ids = {str(row.get('player_id', '')).strip() for row in current_fall_data if str(row.get('player_id', '')).strip()}
    
    # バックアップデータをパターン別に分類
    pattern_1_row = []  # 1行のキー
    pattern_2_rows = []  # 2行のキー
    pattern_3plus_rows = []  # 3行以上のキー
    
    for key, rows in backup_key_to_rows.items():
        player_id, year_val = key
        if len(rows) == 1:
            pattern_1_row.append((player_id, rows))
        elif len(rows) == 2:
            pattern_2_rows.append((player_id, rows))
        else:
            pattern_3plus_rows.append((player_id, rows))
    
    print(f"\n  1行のキー: {len(pattern_1_row)}個")
    spring_count_1 = sum(1 for pid, _ in pattern_1_row if pid in spring_player_ids)
    fall_count_1 = sum(1 for pid, _ in pattern_1_row if pid in fall_player_ids)
    print(f"    春に分類: {spring_count_1}個")
    print(f"    秋に分類: {fall_count_1}個")
    
    print(f"\n  2行のキー: {len(pattern_2_rows)}個")
    spring_count_2 = sum(1 for pid, _ in pattern_2_rows if pid in spring_player_ids)
    fall_count_2 = sum(1 for pid, _ in pattern_2_rows if pid in fall_player_ids)
    print(f"    春に分類: {spring_count_2}個（各行が1つずつ）")
    print(f"    秋に分類: {fall_count_2}個（各行が1つずつ）")
    print(f"    期待値: 春{len(pattern_2_rows)}個、秋{len(pattern_2_rows)}個")
    
    print(f"\n  3行以上のキー: {len(pattern_3plus_rows)}個")
    total_rows_3plus = sum(len(rows) for _, rows in pattern_3plus_rows)
    print(f"    総行数: {total_rows_3plus}行")
    
    # 3行以上のキーがどう分割されたかを詳しく調査
    print(f"\n  3行以上のキーの分割詳細（最初の10個）:")
    for i, (player_id, rows) in enumerate(pattern_3plus_rows[:10], 1):
        spring_rows_for_player = [row for row in current_spring_data if str(row.get('player_id', '')).strip() == player_id]
        fall_rows_for_player = [row for row in current_fall_data if str(row.get('player_id', '')).strip() == player_id]
        
        print(f"\n  {i}. player_id: {player_id}")
        print(f"     バックアップ: {len(rows)}行")
        print(f"     現在の春: {len(spring_rows_for_player)}行")
        print(f"     現在の秋: {len(fall_rows_for_player)}行")
        print(f"     合計: {len(spring_rows_for_player) + len(fall_rows_for_player)}行（期待値: {len(rows)}行）")
        
        # 統計データを表示
        print(f"     バックアップデータの統計:")
        for j, row in enumerate(rows, 1):
            print(f"       行{j}: G={row.get('G')}, PA={row.get('PA')}, AB={row.get('AB')}, H={row.get('H')}")
    
    # 分割ロジックの問題点を特定
    print("\n" + "=" * 80)
    print("問題の原因分析")
    print("=" * 80)
    
    # 3行以上のキーの処理で、最初の1行を春、残りを秋に振り分けた影響を計算
    expected_spring_from_3plus = len(pattern_3plus_rows)  # 各キーの最初の1行
    expected_fall_from_3plus = total_rows_3plus - len(pattern_3plus_rows)  # 残りの行
    
    actual_spring_count = len([pid for pid in spring_player_ids if any(pid == p for p, _ in pattern_3plus_rows)])
    actual_fall_rows = sum(len([row for row in current_fall_data if str(row.get('player_id', '')).strip() == pid]) 
                          for pid, _ in pattern_3plus_rows)
    
    print(f"\n[3行以上のキーの分割ロジックの影響]")
    print(f"  3行以上のキー数: {len(pattern_3plus_rows)}個")
    print(f"  総行数: {total_rows_3plus}行")
    print(f"  期待される春への振り分け: {expected_spring_from_3plus}行（各キーの最初の1行）")
    print(f"  期待される秋への振り分け: {expected_fall_from_3plus}行（残りの行）")
    print(f"  実際の秋の行数（該当プレイヤー）: {actual_fall_rows}行")
    print(f"\n  → 3行以上のキーの処理により、秋に多くの行が集中している可能性")
    
    # 重複の原因
    print(f"\n[秋シーズンの重複の原因]")
    print(f"  秋の重複プレイヤー数: {len(fall_duplicates)}人")
    print(f"  これらのプレイヤーのバックアップでの状態:")
    
    duplicate_causes = defaultdict(int)
    for player_id in fall_duplicates.keys():
        key = (player_id, '1937')
        if key in backup_key_to_rows:
            row_count = len(backup_key_to_rows[key])
            duplicate_causes[row_count] += 1
    
    for row_count, player_count in sorted(duplicate_causes.items()):
        print(f"    {row_count}行あったキー: {player_count}人")
    
    print(f"\n  → 3行以上のキーを処理する際、最初の1行を春、残りを秋に振り分けた結果、")
    print(f"     秋に複数行が含まれ、重複が発生している")
    
    # 推奨事項
    print("\n" + "=" * 80)
    print("推奨事項")
    print("=" * 80)
    
    print(f"\n1. 3行以上のキーの処理方法を改善:")
    print(f"   - 現在: 最初の1行を春、残りを秋に振り分け")
    print(f"   - 推奨: jbl参照データと統計データでマッチングして正確に分割")
    print(f"   - または: 2行ずつペアにして春・秋に振り分け（2行を超える場合は最初の2行、次の2行...）")
    
    print(f"\n2. 重複の解消:")
    print(f"   - 秋シーズンの重複37人を、統計データやjblデータと照合して正しく分割")
    print(f"   - player_id + 統計データの組み合わせで一意に識別できる可能性が高い")
    
    print(f"\n3. 分割ロジックの見直し:")
    print(f"   - 3行以上のキーは、統計データ（G, PA, AB, H, HR等）でjblデータとマッチング")
    print(f"   - マッチできない場合は、2行ずつペアにして処理")
    
    return 0


if __name__ == '__main__':
    exit(main())





















