#!/usr/bin/env python3
"""
final_check_1937_1936.py

1936/1937年の4シーズンファイルの最終確認
"""

import csv
from pathlib import Path
from typing import List, Dict, Any
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


def check_duplicates(data: List[Dict[str, Any]], season_name: str) -> tuple:
    """重複チェック"""
    player_ids = defaultdict(int)
    for row in data:
        player_id = str(row.get('player_id', '')).strip()
        if player_id:
            player_ids[player_id] += 1
    
    duplicates = {pid: count for pid, count in player_ids.items() if count > 1}
    return len(duplicates), duplicates


def main():
    base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")
    output_dir = base_path / "data" / "batting" / "yearly_from_master_dedup"
    
    print("=" * 80)
    print("1936/1937年 4シーズンファイル 最終確認")
    print("=" * 80)
    
    # 確認対象ファイル
    files_to_check = {
        '1936春': output_dir / "batting_1936_spring_PRE.csv",
        '1936秋': output_dir / "batting_1936_fall_PRE.csv",
        '1937春': output_dir / "batting_1937_spring_PRE.csv",
        '1937秋': output_dir / "batting_1937_fall_PRE.csv",
    }
    
    all_good = True
    
    print("\n[ファイル存在確認]")
    for name, path in files_to_check.items():
        if path.exists():
            print(f"  {name}: OK")
        else:
            print(f"  {name}: NG（ファイルが見つかりません）")
            all_good = False
    
    if not all_good:
        print("\n[エラー] 一部のファイルが見つかりません。")
        return 1
    
    print("\n[データ内容確認]")
    results = {}
    
    for name, path in files_to_check.items():
        try:
            data = load_csv_with_encoding(path)
            dup_count, duplicates = check_duplicates(data, name)
            
            results[name] = {
                'row_count': len(data),
                'duplicate_count': dup_count,
                'has_duplicates': dup_count > 0,
                'unique_players': len(set(str(row.get('player_id', '')).strip() for row in data if str(row.get('player_id', '')).strip()))
            }
            
            status = "OK" if dup_count == 0 else "NG"
            print(f"  {name}: {len(data)}行、ユニークプレイヤー{results[name]['unique_players']}人、重複{dup_count}人 -> {status}")
            
            if dup_count > 0:
                all_good = False
                print(f"    重複プレイヤー: {list(duplicates.keys())[:5]}")
        
        except Exception as e:
            print(f"  {name}: エラー - {e}")
            all_good = False
    
    # 合計確認
    print("\n[合計データ]")
    total_rows = sum(r['row_count'] for r in results.values())
    total_unique = sum(r['unique_players'] for r in results.values())
    print(f"  総行数: {total_rows}行")
    print(f"  総ユニークプレイヤー数（重複カウント）: {total_unique}人")
    
    # 1936年合計
    rows_1936 = results.get('1936春', {}).get('row_count', 0) + results.get('1936秋', {}).get('row_count', 0)
    print(f"  1936年合計: {rows_1936}行")
    
    # 1937年合計
    rows_1937 = results.get('1937春', {}).get('row_count', 0) + results.get('1937秋', {}).get('row_count', 0)
    print(f"  1937年合計: {rows_1937}行")
    
    # 最終判定
    print("\n" + "=" * 80)
    print("最終判定")
    print("=" * 80)
    
    if all_good:
        print("\n[OK] 完成品として問題ありません")
        print("\n  確認項目:")
        print("    - 4ファイル全てが存在する")
        print("    - 全ファイルで重複なし")
        print("    - データが正常に読み込める")
        print("\n  ファイル:")
        for name, path in files_to_check.items():
            row_count = results[name]['row_count']
            print(f"    - {name}: {path.name} ({row_count}行)")
        print(f"\n  保存先: {output_dir}")
        return 0
    else:
        print("\n[NG] 問題があります。上記のエラーを確認してください。")
        return 1


if __name__ == '__main__':
    exit(main())





















