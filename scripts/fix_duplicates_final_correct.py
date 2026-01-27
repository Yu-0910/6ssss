#!/usr/bin/env python3
"""
fix_duplicates_final_correct.py

重複を正確に解消する（統計データで既存データと比較）
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
    """統計データからキーを生成"""
    key_fields = ['G', 'PA', 'AB', 'H', 'HR', 'RBI', 'team']
    key_values = []
    for field in key_fields:
        val = str(row.get(field, '')).strip()
        key_values.append(val if val else '0')
    return tuple(key_values)


def safe_float(value: Any) -> float:
    """安全にfloatに変換"""
    try:
        return float(value) if value else 0.0
    except:
        return 0.0


def main():
    base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")
    
    # 現在の分割データ
    current_spring_path = base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_spring_PRE.csv"
    current_fall_path = base_path / "data" / "batting" / "yearly_from_master_dedup" / "batting_1937_fall_PRE.csv"
    
    # バックアップファイル
    backup_path = base_path / "data" / "batting" / "backups" / "20251222_014659" / "yearly_from_master" / "batting_1937_PRE_from_master.csv"
    
    output_dir = base_path / "data" / "batting" / "yearly_from_master_dedup"
    
    print("=" * 80)
    print("重複を正確に解消（統計データで既存データと比較）")
    print("=" * 80)
    
    # 現在のデータを読み込む
    print("\n[読み込み] 現在のデータ")
    spring_data = load_csv_with_encoding(current_spring_path)
    fall_data = load_csv_with_encoding(current_fall_path)
    
    print(f"  春: {len(spring_data)}行")
    print(f"  秋: {len(fall_data)}行")
    
    # 重複を探す
    spring_player_ids = defaultdict(list)
    fall_player_ids = defaultdict(list)
    
    for idx, row in enumerate(spring_data):
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            spring_player_ids[player_id].append((idx, row))
    
    for idx, row in enumerate(fall_data):
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            fall_player_ids[player_id].append((idx, row))
    
    spring_duplicates = {pid: rows for pid, rows in spring_player_ids.items() if len(rows) > 1}
    fall_duplicates = {pid: rows for pid, rows in fall_player_ids.items() if len(rows) > 1}
    
    print(f"\n[重複プレイヤー]")
    print(f"  春の重複: {len(spring_duplicates)}人")
    print(f"  秋の重複: {len(fall_duplicates)}人")
    
    # バックアップデータを読み込んで、重複除去済みデータを取得
    print(f"\n[読み込み] バックアップデータ（重複除去用）")
    backup_data = load_csv_with_encoding(backup_path)
    backup_1937_data = [row for row in backup_data if '1937' in str(row.get('year', '')).strip()]
    
    # 重複除去
    key_to_rows = defaultdict(list)
    for row in backup_1937_data:
        player_id = str(row.get('player_id', '')).strip()
        year_val = str(row.get('year', '')).strip()
        key = (player_id, year_val)
        key_to_rows[key].append(row)
    
    deduplicated_key_to_rows = {}
    for key, rows in key_to_rows.items():
        seen_stats = {}
        deduplicated = []
        for row in rows:
            stats_key = create_stats_key(row)
            if stats_key not in seen_stats:
                seen_stats[stats_key] = row
                deduplicated.append(row)
        deduplicated_key_to_rows[key] = deduplicated
    
    # 新しい春・秋データを作成（重複を除外）
    spring_data_new = []
    fall_data_new = []
    
    # 既に存在する統計データを記録
    existing_spring_stats = set()
    existing_fall_stats = set()
    
    # 重複していないプレイヤーはそのまま追加
    for row in spring_data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id not in spring_duplicates:
            spring_data_new.append(row)
            stats_key = create_stats_key(row)
            existing_spring_stats.add((player_id, stats_key))
    
    for row in fall_data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id not in fall_duplicates:
            fall_data_new.append(row)
            stats_key = create_stats_key(row)
            existing_fall_stats.add((player_id, stats_key))
    
    # 重複プレイヤーを処理
    all_duplicates = set(list(spring_duplicates.keys()) + list(fall_duplicates.keys()))
    
    print(f"\n[重複プレイヤーの処理]")
    for player_id in all_duplicates:
        print(f"\n  player_id: {player_id}")
        
        key = (player_id, '1937')
        if key in deduplicated_key_to_rows:
            backup_rows = deduplicated_key_to_rows[key]
            print(f"    バックアップ（重複除去後）: {len(backup_rows)}行")
            
            # 既存の統計データと比較して、重複しない行のみを追加
            for row in backup_rows:
                stats_key = create_stats_key(row)
                
                # 既に存在する統計データはスキップ
                if (player_id, stats_key) in existing_spring_stats:
                    print(f"      スキップ（春に既存）: G={row.get('G')}, PA={row.get('PA')}, H={row.get('H')}")
                    continue
                
                if (player_id, stats_key) in existing_fall_stats:
                    print(f"      スキップ（秋に既存）: G={row.get('G')}, PA={row.get('PA')}, H={row.get('H')}")
                    continue
                
                # 新しい統計データの場合、G, PAで判定して分割
                g_value = safe_float(row.get('G', 0))
                pa_value = safe_float(row.get('PA', 0))
                
                if g_value < 30 and pa_value < 100:
                    spring_data_new.append(row)
                    existing_spring_stats.add((player_id, stats_key))
                    print(f"      -> 春に追加: G={row.get('G')}, PA={row.get('PA')}, H={row.get('H')}")
                else:
                    fall_data_new.append(row)
                    existing_fall_stats.add((player_id, stats_key))
                    print(f"      -> 秋に追加: G={row.get('G')}, PA={row.get('PA')}, H={row.get('H')}")
        else:
            print(f"    警告: バックアップデータに見つかりません")
    
    # 最終確認
    print(f"\n[最終確認] 重複チェック")
    spring_player_ids_final = defaultdict(int)
    fall_player_ids_final = defaultdict(int)
    
    for row in spring_data_new:
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            spring_player_ids_final[player_id] += 1
    
    for row in fall_data_new:
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            fall_player_ids_final[player_id] += 1
    
    spring_duplicates_final = {pid: count for pid, count in spring_player_ids_final.items() if count > 1}
    fall_duplicates_final = {pid: count for pid, count in fall_player_ids_final.items() if count > 1}
    
    if spring_duplicates_final:
        print(f"  春の重複: {len(spring_duplicates_final)}人")
        for pid, count in spring_duplicates_final.items():
            print(f"    player_id {pid}: {count}回")
    else:
        print(f"  春の重複: なし")
    
    if fall_duplicates_final:
        print(f"  秋の重複: {len(fall_duplicates_final)}人")
        for pid, count in fall_duplicates_final.items():
            print(f"    player_id {pid}: {count}回")
    else:
        print(f"  秋の重複: なし")
    
    # 保存
    fieldnames = list(spring_data[0].keys()) if spring_data else []
    if not fieldnames:
        with open(current_spring_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
    
    spring_path = output_dir / "batting_1937_spring_PRE.csv"
    save_csv(spring_data_new, spring_path, fieldnames=fieldnames)
    
    fall_path = output_dir / "batting_1937_fall_PRE.csv"
    save_csv(fall_data_new, fall_path, fieldnames=fieldnames)
    
    print("\n" + "=" * 80)
    print("処理完了")
    print("=" * 80)
    print(f"\n[結果]")
    print(f"  春: {len(spring_data_new)}行")
    print(f"  秋: {len(fall_data_new)}行")
    print(f"  合計: {len(spring_data_new) + len(fall_data_new)}行")
    
    return 0


if __name__ == '__main__':
    exit(main())





















