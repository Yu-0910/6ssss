#!/usr/bin/env python3
"""
fix_1937_split_with_dedup.py

バックアップデータから重複を除去してから1937年を春秋に分割する
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


def create_stats_key(row: Dict[str, Any]) -> Tuple:
    """統計データからキーを生成（重複除去用）"""
    key_fields = ['G', 'PA', 'AB', 'H', 'HR', 'RBI', 'team']
    key_values = []
    for field in key_fields:
        val = str(row.get(field, '')).strip()
        key_values.append(val if val else '0')
    return tuple(key_values)


def deduplicate_by_stats(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """統計データで重複を除去"""
    seen_stats = {}
    deduplicated = []
    
    for row in rows:
        stats_key = create_stats_key(row)
        if stats_key not in seen_stats:
            seen_stats[stats_key] = row
            deduplicated.append(row)
    
    return deduplicated


def create_player_stats_key(row: Dict[str, Any]) -> Tuple:
    """プレイヤーの統計からキーを生成（jblマッチング用）"""
    key_fields = ['G', 'PA', 'AB', 'H', 'HR']
    key_values = []
    for field in key_fields:
        val = str(row.get(field, '')).strip()
        key_values.append(val if val else '0')
    return tuple(key_values)


def main():
    base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")
    
    # バックアップファイル
    backup_path = base_path / "data" / "batting" / "backups" / "20251222_014659" / "yearly_from_master" / "batting_1937_PRE_from_master.csv"
    
    # jbl参照データ
    jbl_spring_path = base_path / "data" / "batting" / "jbl" / "batting_1937S_from_individual.csv"
    jbl_fall_path = base_path / "data" / "batting" / "jbl" / "batting_1937A_from_individual.csv"
    
    # 出力先
    output_dir = base_path / "data" / "batting" / "yearly_from_master_dedup"
    
    print("=" * 80)
    print("1937年データの重複除去と再分割")
    print("=" * 80)
    
    # バックアップデータを読み込む
    print(f"\n[読み込み] バックアップファイル")
    backup_data = load_csv_with_encoding(backup_path)
    backup_1937_data = [row for row in backup_data if '1937' in str(row.get('year', '')).strip()]
    print(f"  1937年データ: {len(backup_1937_data)}行")
    
    # player_id + yearでグループ化
    key_to_rows = defaultdict(list)
    for row in backup_1937_data:
        player_id = str(row.get('player_id', '')).strip()
        year_val = str(row.get('year', '')).strip()
        key = (player_id, year_val)
        key_to_rows[key].append(row)
    
    print(f"  ユニークキー数: {len(key_to_rows)}個")
    
    # 重複除去：各キーについて統計データで重複を除去
    print(f"\n[重複除去] 統計データで重複を除去")
    deduplicated_key_to_rows = {}
    total_before = 0
    total_after = 0
    
    for key, rows in key_to_rows.items():
        total_before += len(rows)
        deduplicated = deduplicate_by_stats(rows)
        deduplicated_key_to_rows[key] = deduplicated
        total_after += len(deduplicated)
        if len(rows) != len(deduplicated):
            player_id = key[0]
            print(f"  player_id {player_id}: {len(rows)}行 -> {len(deduplicated)}行（{len(rows) - len(deduplicated)}行の重複を除去）")
    
    print(f"  重複除去前: {total_before}行")
    print(f"  重複除去後: {total_after}行")
    print(f"  除去された行数: {total_before - total_after}行")
    
    # jbl参照データを読み込む
    print(f"\n[読み込み] jbl参照データ")
    jbl_spring_data = load_csv_with_encoding(jbl_spring_path) if jbl_spring_path.exists() else []
    jbl_fall_data = load_csv_with_encoding(jbl_fall_path) if jbl_fall_path.exists() else []
    
    print(f"  jbl春: {len(jbl_spring_data)}行")
    print(f"  jbl秋: {len(jbl_fall_data)}行")
    
    # jblデータからマッチング用のマップを作成
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
    
    # player_idのセットも作成（フォールバック用）
    jbl_spring_player_ids = {str(row.get('player_id', '')).strip() for row in jbl_spring_data if str(row.get('player_id', '')).strip()}
    jbl_fall_player_ids = {str(row.get('player_id', '')).strip() for row in jbl_fall_data if str(row.get('player_id', '')).strip()}
    
    # 分割処理
    print(f"\n[分割処理]")
    spring_data = []
    fall_data = []
    unmatched_data = []
    
    for key, rows in deduplicated_key_to_rows.items():
        player_id, year_val = key
        
        if len(rows) == 1:
            # 1行の場合：jblデータとマッチング
            row = rows[0]
            stats_key = create_player_stats_key(row)
            
            if (player_id, stats_key) in jbl_spring_keys or player_id in jbl_spring_player_ids:
                spring_data.append(row)
            elif (player_id, stats_key) in jbl_fall_keys or player_id in jbl_fall_player_ids:
                fall_data.append(row)
            else:
                unmatched_data.append(row)
        
        elif len(rows) == 2:
            # 2行の場合：jblデータとマッチングして分割
            row1, row2 = rows
            stats_key1 = create_player_stats_key(row1)
            stats_key2 = create_player_stats_key(row2)
            
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
        
        else:
            # 3行以上の場合：jblデータとマッチングして分割
            matched_spring = []
            matched_fall = []
            unmatched_rows = []
            
            for row in rows:
                stats_key = create_player_stats_key(row)
                if (player_id, stats_key) in jbl_spring_keys:
                    matched_spring.append(row)
                elif (player_id, stats_key) in jbl_fall_keys:
                    matched_fall.append(row)
                else:
                    unmatched_rows.append(row)
            
            # マッチしたものを追加
            spring_data.extend(matched_spring)
            fall_data.extend(matched_fall)
            
            # マッチしなかった行を処理
            if unmatched_rows:
                # player_idで判定（フォールバック）
                if player_id in jbl_spring_player_ids and player_id not in jbl_fall_player_ids:
                    spring_data.extend(unmatched_rows)
                elif player_id in jbl_fall_player_ids and player_id not in jbl_spring_player_ids:
                    fall_data.extend(unmatched_rows)
                else:
                    # どちらにも含まれない場合は、最初の1行を春、残りを秋に
                    if unmatched_rows:
                        spring_data.append(unmatched_rows[0])
                        fall_data.extend(unmatched_rows[1:])
    
    print(f"  春: {len(spring_data)}行")
    print(f"  秋: {len(fall_data)}行")
    print(f"  マッチしなかったデータ: {len(unmatched_data)}行")
    
    # マッチしなかったデータを処理
    if unmatched_data:
        print(f"\n[注意] マッチしなかった{len(unmatched_data)}行を春のデータに含めます")
        spring_data.extend(unmatched_data)
    
    # 重複チェック（最終確認）
    print(f"\n[最終確認] 重複チェック")
    spring_player_ids = defaultdict(int)
    fall_player_ids = defaultdict(int)
    
    for row in spring_data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            spring_player_ids[player_id] += 1
    
    for row in fall_data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            fall_player_ids[player_id] += 1
    
    spring_duplicates = {pid: count for pid, count in spring_player_ids.items() if count > 1}
    fall_duplicates = {pid: count for pid, count in fall_player_ids.items() if count > 1}
    
    if spring_duplicates:
        print(f"  春の重複プレイヤー: {len(spring_duplicates)}人")
        for pid, count in list(spring_duplicates.items())[:5]:
            print(f"    player_id {pid}: {count}回")
    else:
        print(f"  春の重複: なし")
    
    if fall_duplicates:
        print(f"  秋の重複プレイヤー: {len(fall_duplicates)}人")
        for pid, count in list(fall_duplicates.items())[:5]:
            print(f"    player_id {pid}: {count}回")
    else:
        print(f"  秋の重複: なし")
    
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
    print(f"  合計: {len(spring_data) + len(fall_data)}行（重複除去後: {total_after}行から）")
    print(f"  重複除去前: {total_before}行")
    print(f"  改善: {total_before - (len(spring_data) + len(fall_data))}行の重複を除去")
    
    return 0


if __name__ == '__main__':
    exit(main())





















