#!/usr/bin/env python3
"""
remove_duplicate_players_from_csv.py

CSVファイルから重複選手を削除するスクリプト
同じplayer_idで異なるチーム名の行がある場合、最初の行を残し、残りを削除する。

重要: 両方とも削除することは絶対に禁止
"""

import csv
import argparse
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

def load_csv_with_encoding(csv_path: Path) -> List[Dict[str, str]]:
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

def find_duplicates_in_csv(rows: List[Dict[str, str]]) -> Dict[str, List[int]]:
    """
    CSV内の重複を検出
    
    Returns:
        {player_id: [row_indices]}
    """
    player_id_to_indices = defaultdict(list)
    
    for idx, row in enumerate(rows):
        player_id = row.get('player_id', '').strip()
        if player_id:
            player_id_to_indices[player_id].append(idx)
    
    # 2つ以上出現するplayer_idのみを返す
    return {pid: indices for pid, indices in player_id_to_indices.items() if len(indices) >= 2}

def determine_removal_indices(duplicates: Dict[str, List[int]], rows: List[Dict[str, str]]) -> Set[int]:
    """
    削除対象の行インデックスを決定
    
    基準: 最初に出現した行を残し、残りを削除
    """
    removal_indices = set()
    
    for player_id, indices in duplicates.items():
        # 最初の行を残す、残りを削除
        if len(indices) > 1:
            # 最初の行を残す
            keep_index = indices[0]
            # 残りを削除対象に追加
            for idx in indices[1:]:
                removal_indices.add(idx)
    
    return removal_indices

def remove_duplicates_from_csv(csv_path: Path, dry_run: bool = False) -> int:
    """
    CSVファイルから重複選手を削除
    
    Returns:
        削除した行数
    """
    # CSVを読み込む
    rows = load_csv_with_encoding(csv_path)
    
    if not rows:
        return 0
    
    # 重複を検出
    duplicates = find_duplicates_in_csv(rows)
    
    if not duplicates:
        return 0
    
    # 削除対象を決定
    removal_indices = determine_removal_indices(duplicates, rows)
    
    if not removal_indices:
        return 0
    
    # ドライランの場合は削除しない
    if dry_run:
        return len(removal_indices)
    
    # 削除（必ず片方だけを削除）
    original_count = len(rows)
    rows = [row for idx, row in enumerate(rows) if idx not in removal_indices]
    removed_count = original_count - len(rows)
    
    # 安全チェック: すべての行を削除していないか確認
    if len(rows) == 0:
        print(f"[エラー] {csv_path} で全行が削除されそうになりました。処理を中止します。")
        return 0
    
    # ヘッダーを取得
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
    
    if not fieldnames:
        print(f"[エラー] {csv_path} のヘッダーを読み込めませんでした。")
        return 0
    
    # CSVを保存
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return removed_count

def main():
    parser = argparse.ArgumentParser(description='CSVファイルから重複選手を削除')
    parser.add_argument('--dry-run', action='store_true', help='ドライラン（実際には削除しない）')
    parser.add_argument('--year', type=int, help='対象年度（指定しない場合は全年度）')
    parser.add_argument('--league', type=str, help='対象リーグ（指定しない場合は全リーグ）')
    parser.add_argument('--csv-dir', type=str, default='_data/master_csv_calculated', 
                       help='CSVファイルのディレクトリ（デフォルト: _data/master_csv_calculated）')
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.resolve()
    csv_dir = project_root / args.csv_dir
    
    print("=" * 80)
    print("CSVファイル内の重複選手削除")
    print("=" * 80)
    print(f"対象ディレクトリ: {csv_dir}")
    if args.dry_run:
        print("[モード] ドライラン（実際には削除しません）")
    else:
        print("[モード] 本番実行")
    if args.year:
        print(f"対象年度: {args.year}")
    if args.league:
        print(f"対象リーグ: {args.league}")
    print()
    
    # CSVディレクトリの存在確認
    if not csv_dir.exists():
        print(f"[エラー] CSVディレクトリが見つかりません: {csv_dir}")
        return 1
    
    # CSVファイルを探索
    print("CSVファイルを探索中...")
    csv_files = []
    for csv_file in csv_dir.glob("batting_*_from_master.csv"):
        # ファイル名から年度・リーグを抽出
        # 例: batting_1973_PL_from_master.csv
        parts = csv_file.stem.split('_')
        if len(parts) >= 3:
            try:
                year = int(parts[1])
                league = parts[2].upper()
                
                if args.year and year != args.year:
                    continue
                if args.league and league != args.league.upper():
                    continue
                
                csv_files.append(csv_file)
            except ValueError:
                continue
    
    print(f"  見つかったファイル数: {len(csv_files)}")
    
    if not csv_files:
        print("[警告] 対象のCSVファイルが見つかりませんでした。")
        return 0
    
    # 処理
    print("\n重複選手を削除中...")
    total_removed = 0
    processed_files = 0
    
    for csv_file in csv_files:
        try:
            removed_count = remove_duplicates_from_csv(csv_file, args.dry_run)
            if removed_count > 0:
                total_removed += removed_count
                processed_files += 1
                print(f"  {csv_file.name}: {removed_count} 行削除")
        except Exception as e:
            print(f"  [エラー] {csv_file.name}: {e}")
    
    # 結果表示
    print()
    print("=" * 80)
    print("処理結果")
    print("=" * 80)
    print(f"処理したファイル数: {processed_files}")
    print(f"削除した行数: {total_removed}")
    print()
    
    if args.dry_run:
        print("[注意] ドライランモードでした。実際には削除していません。")
        print("本番実行する場合は --dry-run を外してください。")
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
