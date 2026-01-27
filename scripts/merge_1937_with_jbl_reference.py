#!/usr/bin/env python3
"""
merge_1937_with_jbl_reference.py

jblファイル（既存の分割済みデータ）を参照して、バックアップファイルをより正確に分割する
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


def save_csv(data: List[Dict[str, Any]], output_path: Path, fieldnames: List[str] = None):
    """CSVファイルを保存"""
    if not data:
        print(f"[警告] {output_path.name} に書き込むデータがありません")
        return
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if fieldnames is None:
        fieldnames = list(data[0].keys())
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
    
    print(f"[完了] 保存: {output_path} ({len(data)}行)")


def create_player_stats_key(row: Dict[str, Any]) -> Tuple:
    """プレイヤーの統計からキーを生成（春秋を識別するため）"""
    # 主要な統計指標でキーを作成
    key_fields = ['G', 'PA', 'AB', 'H', 'HR', 'RBI']
    key_values = []
    for field in key_fields:
        val = str(row.get(field, '')).strip()
        key_values.append(val if val else '0')
    return tuple(key_values)


def main():
    base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")
    
    # 参照ファイル（jblの既存分割データ）
    jbl_spring_path = base_path / "data" / "batting" / "jbl" / "batting_1937S_from_individual.csv"
    jbl_fall_path = base_path / "data" / "batting" / "jbl" / "batting_1937A_from_individual.csv"
    
    # バックアップファイル
    backup_path = base_path / "data" / "batting" / "backups" / "20251222_014659" / "yearly_from_master" / "batting_1937_PRE_from_master.csv"
    
    # 出力先
    output_dir = base_path / "data" / "batting" / "yearly_from_master_dedup"
    
    print("=" * 80)
    print("1937年データをjbl参照ファイルを使って分割")
    print("=" * 80)
    
    # jblファイルを読み込んで参照データを作成
    print("\n[読み込み] jbl参照ファイル")
    jbl_spring_data = load_csv_with_encoding(jbl_spring_path) if jbl_spring_path.exists() else []
    jbl_fall_data = load_csv_with_encoding(jbl_fall_path) if jbl_fall_path.exists() else []
    
    print(f"  jbl春: {len(jbl_spring_data)}行")
    print(f"  jbl秋: {len(jbl_fall_data)}行")
    
    # jblデータから player_id -> season のマッピングを作成
    # 統計データでマッチングするため、player_id + 主要統計でキーを作成
    jbl_spring_keys = {}
    jbl_fall_keys = {}
    
    for row in jbl_spring_data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            stats_key = create_player_stats_key(row)
            jbl_spring_keys[(player_id, stats_key)] = row
    
    for row in jbl_fall_data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            stats_key = create_player_stats_key(row)
            jbl_fall_keys[(player_id, stats_key)] = row
    
    print(f"  jbl春キー数: {len(jbl_spring_keys)}")
    print(f"  jbl秋キー数: {len(jbl_fall_keys)}")
    
    # バックアップファイルを読み込む
    print(f"\n[読み込み] バックアップファイル")
    backup_data = load_csv_with_encoding(backup_path)
    print(f"  全行数: {len(backup_data)}行")
    
    # 1937年のデータをフィルタ
    filtered_data = []
    for row in backup_data:
        year_val = str(row.get('year', '')).strip()
        if year_val == '1937' or year_val.startswith('1937'):
            filtered_data.append(row)
    
    print(f"  1937年フィルタ後: {len(filtered_data)}行")
    
    # player_id + year でグループ化
    key_to_rows = defaultdict(list)
    for row in filtered_data:
        player_id = str(row.get('player_id', '')).strip()
        year_val = str(row.get('year', '')).strip()
        key = (player_id, year_val)
        key_to_rows[key].append(row)
    
    # 重複を確認
    duplicates = {k: rows for k, rows in key_to_rows.items() if len(rows) > 1}
    print(f"  重複キー数: {len(duplicates)}件")
    
    spring_data = []
    fall_data = []
    unmatched_data = []
    
    # jblデータからplayer_idのセットを作成（簡単なマッチング用）
    jbl_spring_player_ids = set()
    jbl_fall_player_ids = set()
    
    for row in jbl_spring_data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            jbl_spring_player_ids.add(player_id)
    
    for row in jbl_fall_data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            jbl_fall_player_ids.add(player_id)
    
    # 各行を処理（全行を必ず含める）
    processed_keys = set()
    total_processed = 0
    for key, rows in key_to_rows.items():
        player_id, year_val = key
        
        if len(rows) == 2:
            # 2行の場合：統計データでjblデータとマッチングして分割
            row1, row2 = rows
            stats_key1 = create_player_stats_key(row1)
            stats_key2 = create_player_stats_key(row2)
            
            # jblデータとマッチング
            match1_spring = (player_id, stats_key1) in jbl_spring_keys
            match1_fall = (player_id, stats_key1) in jbl_fall_keys
            match2_spring = (player_id, stats_key2) in jbl_spring_keys
            match2_fall = (player_id, stats_key2) in jbl_fall_keys
            
            if match1_spring and match2_fall:
                spring_data.append(row1)
                fall_data.append(row2)
            elif match1_fall and match2_spring:
                spring_data.append(row2)
                fall_data.append(row1)
            elif match1_spring or (player_id in jbl_spring_player_ids and not match1_fall):
                spring_data.append(row1)
                fall_data.append(row2)
            elif match1_fall or (player_id in jbl_fall_player_ids and not match1_spring):
                fall_data.append(row1)
                spring_data.append(row2)
            elif match2_spring:
                spring_data.append(row2)
                fall_data.append(row1)
            elif match2_fall:
                fall_data.append(row2)
                spring_data.append(row1)
            else:
                # マッチしない場合は最初を春、2番目を秋に
                spring_data.append(row1)
                fall_data.append(row2)
            
            processed_keys.add(key)
            total_processed += 2
        elif len(rows) == 1:
            # 1行の場合：jblデータとマッチング
            row = rows[0]
            stats_key = create_player_stats_key(row)
            
            if (player_id, stats_key) in jbl_spring_keys or player_id in jbl_spring_player_ids:
                spring_data.append(row)
            elif (player_id, stats_key) in jbl_fall_keys or player_id in jbl_fall_player_ids:
                fall_data.append(row)
            else:
                # マッチしない場合は春に含める
                unmatched_data.append(row)
            
            processed_keys.add(key)
            total_processed += 1
        else:
            # 3行以上の場合：最初の1行を春、残りを秋に（簡易的な処理）
            # より正確な処理が必要な場合は、jblデータとマッチングする
            spring_data.append(rows[0])
            fall_data.extend(rows[1:])
            
            processed_keys.add(key)
            total_processed += len(rows)
    
    print(f"\n[デバッグ] 処理した行数: {total_processed}行（期待値: {len(filtered_data)}行）")
    
    print(f"\n[分割結果]")
    print(f"  春: {len(spring_data)}行")
    print(f"  秋: {len(fall_data)}行")
    print(f"  マッチしなかったデータ: {len(unmatched_data)}行")
    print(f"  合計: {len(spring_data) + len(fall_data) + len(unmatched_data)}行")
    
    # マッチしなかったデータを処理（全て春に含める）
    if unmatched_data:
        print(f"\n[注意] マッチしなかった{len(unmatched_data)}行を春のデータに含めます")
        spring_data.extend(unmatched_data)
    
    # 保存
    fieldnames = list(backup_data[0].keys())
    
    spring_path = output_dir / "batting_1937_spring_PRE.csv"
    save_csv(spring_data, spring_path, fieldnames=fieldnames)
    
    fall_path = output_dir / "batting_1937_fall_PRE.csv"
    save_csv(fall_data, fall_path, fieldnames=fieldnames)
    
    print("\n" + "=" * 80)
    print("処理完了")
    print("=" * 80)
    print(f"\n[結果]")
    print(f"  春: {len(spring_data)}行")
    print(f"  秋: {len(fall_data)}行")
    print(f"  合計: {len(spring_data) + len(fall_data)}行（元の{len(filtered_data)}行から）")
    
    return 0


if __name__ == '__main__':
    exit(main())

