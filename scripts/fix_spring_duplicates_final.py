#!/usr/bin/env python3
"""
fix_spring_duplicates_final.py

春の重複を最終的に解消する
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
    print("春の重複を最終的に解消")
    print("=" * 80)
    
    # 現在のデータを読み込む
    print("\n[読み込み] 現在のデータ")
    spring_data = load_csv_with_encoding(current_spring_path)
    fall_data = load_csv_with_encoding(current_fall_path)
    
    print(f"  春: {len(spring_data)}行")
    print(f"  秋: {len(fall_data)}行")
    
    # 春の重複を探す
    spring_player_ids = defaultdict(list)
    for idx, row in enumerate(spring_data):
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            spring_player_ids[player_id].append((idx, row))
    
    spring_duplicates = {pid: rows for pid, rows in spring_player_ids.items() if len(rows) > 1}
    
    print(f"\n[春の重複プレイヤー]")
    print(f"  重複プレイヤー数: {len(spring_duplicates)}人")
    
    if not spring_duplicates:
        print("  重複はありませんでした。")
        return 0
    
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
    
    # 春データから重複プレイヤーの行を削除
    spring_data_new = []
    removed_from_spring = []
    
    for idx, row in enumerate(spring_data):
        player_id = str(row.get('player_id', '')).strip()
        if player_id in spring_duplicates:
            removed_from_spring.append((player_id, row))
        else:
            spring_data_new.append(row)
    
    print(f"  春から削除した行数: {len(removed_from_spring)}行")
    
    # 各重複プレイヤーについて、正しい分割を決定
    for player_id, duplicate_rows in spring_duplicates.items():
        print(f"\n  player_id: {player_id}")
        print(f"    重複数: {len(duplicate_rows)}行")
        
        # バックアップデータから該当プレイヤーの重複除去済みデータを取得
        key = (player_id, '1937')
        if key in deduplicated_key_to_rows:
            backup_rows = deduplicated_key_to_rows[key]
            print(f"    バックアップ（重複除去後）: {len(backup_rows)}行")
            
            # 統計データで比較して、春・秋に分割
            spring_rows = []
            fall_rows = []
            
            for row in backup_rows:
                g_value = safe_float(row.get('G', 0))
                pa_value = safe_float(row.get('PA', 0))
                
                # G（試合数）とPA（打席数）が少ない方を春とする
                # 一般的に、春の方が試合数・打席数が少ない傾向がある
                if g_value < 30 and pa_value < 100:
                    spring_rows.append(row)
                    print(f"      -> 春に分類: G={row.get('G')}, PA={row.get('PA')}, H={row.get('H')}")
                else:
                    fall_rows.append(row)
                    print(f"      -> 秋に分類: G={row.get('G')}, PA={row.get('PA')}, H={row.get('H')}")
            
            # 結果を追加
            spring_data_new.extend(spring_rows)
            fall_data.extend(fall_rows)
            
            print(f"    結果: 春{len(spring_rows)}行、秋{len(fall_rows)}行")
        else:
            print(f"    警告: バックアップデータに見つかりません")
            # 見つからない場合は、最初の1行を春、残りを秋に
            if duplicate_rows:
                spring_data_new.append(duplicate_rows[0][1])
                for _, row in duplicate_rows[1:]:
                    fall_data.append(row)
    
    # 保存
    fieldnames = list(spring_data[0].keys()) if spring_data else []
    if not fieldnames:
        with open(current_spring_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
    
    spring_path = output_dir / "batting_1937_spring_PRE.csv"
    save_csv(spring_data_new, spring_path, fieldnames=fieldnames)
    
    fall_path = output_dir / "batting_1937_fall_PRE.csv"
    save_csv(fall_data, fall_path, fieldnames=fieldnames)
    
    # 最終確認
    print(f"\n[最終確認] 重複チェック")
    spring_player_ids_final = defaultdict(int)
    fall_player_ids_final = defaultdict(int)
    
    for row in spring_data_new:
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            spring_player_ids_final[player_id] += 1
    
    for row in fall_data:
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
    
    print("\n" + "=" * 80)
    print("処理完了")
    print("=" * 80)
    print(f"\n[結果]")
    print(f"  春: {len(spring_data_new)}行")
    print(f"  秋: {len(fall_data)}行")
    print(f"  合計: {len(spring_data_new) + len(fall_data)}行")
    
    return 0


if __name__ == '__main__':
    exit(main())





















