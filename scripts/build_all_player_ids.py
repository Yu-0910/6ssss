#!/usr/bin/env python3
"""
STEP 3-0: 1936〜全期間の成績CSV群を走査してplayer_idをユニーク抽出
"""

import csv
import re
from pathlib import Path
from typing import Set, List
import sys

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent


def detect_encoding(file_path: Path) -> str:
    """ファイルの文字コードを検出"""
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)  # 先頭1KBを読んでみる
            return encoding
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return 'utf-8'  # デフォルト


def extract_player_ids_from_csv(csv_path: Path) -> Set[str]:
    """CSVファイルからplayer_idを抽出"""
    player_ids = set()
    encoding = detect_encoding(csv_path)
    
    try:
        with open(csv_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # player_id列の候補名を試す
                for key in row.keys():
                    key_lower = key.lower()
                    if key_lower in ['player_id', 'playerid', 'playerid', 'id', '選手id']:
                        player_id = str(row[key]).strip()
                        if player_id and player_id not in ['', 'nan', 'None', '-']:
                            player_ids.add(player_id)
                        break
    except Exception as e:
        print(f"警告: CSV読み込みエラー ({csv_path}): {e}")
    
    return player_ids


def find_batting_csv_files(search_dirs: List[Path]) -> List[Path]:
    """batting_YYYY_(PL|CL)_from_master.csv パターンのCSVファイルを検索"""
    csv_files = []
    pattern = re.compile(r'batting_\d{4}_(PL|CL)_from_master\.csv$', re.IGNORECASE)
    
    for search_dir in search_dirs:
        if not search_dir.exists() or not search_dir.is_dir():
            continue
        
        # 再帰的に検索
        for csv_file in search_dir.rglob('*.csv'):
            # node_modulesや.nextは除外
            if 'node_modules' in str(csv_file) or '.next' in str(csv_file):
                continue
            
            # パターンに一致するか確認
            if pattern.search(csv_file.name):
                csv_files.append(csv_file)
    
    return sorted(csv_files)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='全期間の成績CSVからplayer_idをユニーク抽出')
    parser.add_argument('--data-dir', type=str, help='成績CSVフォルダのルートディレクトリ（例: C:/data/baseball_csv/）')
    parser.add_argument('--output', type=str, default=None, help='出力CSVファイルパス（デフォルト: output/master/all_player_ids.csv）')
    args = parser.parse_args()
    
    # 探索対象ディレクトリ
    search_dirs = [
        project_root / '_data' / 'master_csv',
        project_root / '_data' / 'master_csv_calculated',
        project_root / '_data',
    ]
    
    # 追加の探索ディレクトリ
    if args.data_dir:
        data_dir = Path(args.data_dir)
        if data_dir.exists():
            search_dirs.append(data_dir)
            print(f"追加探索ディレクトリ: {data_dir}")
        else:
            print(f"警告: 指定されたディレクトリが存在しません: {data_dir}")
            return 1
    
    print("成績CSVファイルを探索中...")
    csv_files = find_batting_csv_files(search_dirs)
    print(f"   見つかったCSVファイル: {len(csv_files)}件\n")
    
    if not csv_files:
        print("エラー: 成績CSVファイルが見つかりませんでした")
        print("   --data-dir オプションで成績CSVフォルダを指定してください")
        return 1
    
    # 各CSVファイルからplayer_idを抽出
    all_player_ids = set()
    processed_files = 0
    
    for csv_file in csv_files:
        print(f"   処理中: {csv_file.name}...", end=' ', flush=True)
        player_ids = extract_player_ids_from_csv(csv_file)
        all_player_ids.update(player_ids)
        processed_files += 1
        print(f"OK: {len(player_ids)}件のplayer_idを抽出")
    
    print(f"\n処理完了: {processed_files}ファイルから {len(all_player_ids)}件のユニークplayer_idを抽出")
    
    # 出力ディレクトリを作成
    output_dir = project_root / 'output' / 'master'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 出力パスを決定
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = output_dir / 'all_player_ids.csv'
    
    # CSVに出力
    sorted_player_ids = sorted(all_player_ids, key=lambda x: (len(x), x))
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['player_id'])
        for player_id in sorted_player_ids:
            writer.writerow([player_id])
    
    print(f"結果を出力しました: {output_path}")
    
    # サマリーを表示
    print(f"\nサマリー:")
    print(f"   処理したCSVファイル数: {processed_files}件")
    print(f"   抽出したユニークplayer_id数: {len(all_player_ids)}件")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())










