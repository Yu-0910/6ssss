#!/usr/bin/env python3
"""
fix_duplicates_one_per_season.py

各プレイヤーをシーズンごとに1行ずつにする（重複を完全に解消）
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
    
    output_dir = base_path / "data" / "batting" / "yearly_from_master_dedup"
    
    print("=" * 80)
    print("各プレイヤーをシーズンごとに1行ずつにする")
    print("=" * 80)
    
    # 現在のデータを読み込む
    print("\n[読み込み] 現在のデータ")
    spring_data = load_csv_with_encoding(current_spring_path)
    fall_data = load_csv_with_encoding(current_fall_path)
    
    print(f"  春: {len(spring_data)}行")
    print(f"  秋: {len(fall_data)}行")
    
    # 各プレイヤーについて、統計データが異なる行を1行ずつにまとめる
    print(f"\n[重複除去処理]")
    
    # 春データ：各player_idについて、最初の1行のみを保持
    spring_data_new = []
    spring_seen_players = set()
    
    for row in spring_data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id and player_id not in spring_seen_players:
            spring_data_new.append(row)
            spring_seen_players.add(player_id)
        elif player_id in spring_seen_players:
            # 重複している場合、統計データが異なる可能性があるため、G+PAの合計が大きい方を選択
            existing_row = next((r for r in spring_data_new if str(r.get('player_id', '')).strip() == player_id), None)
            if existing_row:
                existing_total = safe_float(existing_row.get('G', 0)) + safe_float(existing_row.get('PA', 0))
                new_total = safe_float(row.get('G', 0)) + safe_float(row.get('PA', 0))
                if new_total > existing_total:
                    # より大きな統計データで置き換え
                    spring_data_new = [r for r in spring_data_new if str(r.get('player_id', '')).strip() != player_id]
                    spring_data_new.append(row)
                    print(f"    player_id {player_id}: 春のデータを更新（G+PA: {existing_total:.0f} -> {new_total:.0f}）")
    
    # 秋データ：各player_idについて、最初の1行のみを保持
    fall_data_new = []
    fall_seen_players = set()
    
    for row in fall_data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id and player_id not in fall_seen_players:
            fall_data_new.append(row)
            fall_seen_players.add(player_id)
        elif player_id in fall_seen_players:
            # 重複している場合、統計データが異なる可能性があるため、G+PAの合計が大きい方を選択
            existing_row = next((r for r in fall_data_new if str(r.get('player_id', '')).strip() == player_id), None)
            if existing_row:
                existing_total = safe_float(existing_row.get('G', 0)) + safe_float(existing_row.get('PA', 0))
                new_total = safe_float(row.get('G', 0)) + safe_float(row.get('PA', 0))
                if new_total > existing_total:
                    # より大きな統計データで置き換え
                    fall_data_new = [r for r in fall_data_new if str(r.get('player_id', '')).strip() != player_id]
                    fall_data_new.append(row)
                    print(f"    player_id {player_id}: 秋のデータを更新（G+PA: {existing_total:.0f} -> {new_total:.0f}）")
    
    print(f"\n[重複除去結果]")
    print(f"  春: {len(spring_data)}行 -> {len(spring_data_new)}行（{len(spring_data) - len(spring_data_new)}行削除）")
    print(f"  秋: {len(fall_data)}行 -> {len(fall_data_new)}行（{len(fall_data) - len(fall_data_new)}行削除）")
    
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
    print(f"  春: {len(spring_data_new)}行（重複なし）")
    print(f"  秋: {len(fall_data_new)}行（重複なし）")
    print(f"  合計: {len(spring_data_new) + len(fall_data_new)}行")
    
    return 0


if __name__ == '__main__':
    exit(main())





















