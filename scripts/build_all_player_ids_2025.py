#!/usr/bin/env python3
"""
STEP 1: 2025年の成績CSVからplayer_id（またはplayer_name_ja + team）をユニーク抽出
"""

import csv
import re
from pathlib import Path
from typing import Set, List, Tuple
import sys

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


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


def extract_player_identifiers_from_csv(csv_path: Path) -> List[Tuple[str, str, str]]:
    """
    CSVファイルからplayer_id、player_name_ja、teamを抽出
    
    Returns:
        List[Tuple[player_id, player_name_ja, team]]
    """
    identifiers = []
    encoding = detect_encoding(csv_path)
    
    try:
        with open(csv_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # player_id列を探す
                player_id = ''
                for key in row.keys():
                    key_lower = key.lower()
                    if key_lower in ['player_id', 'playerid', 'id', '選手id']:
                        player_id = str(row[key]).strip()
                        if player_id in ['', 'nan', 'None', '-']:
                            player_id = ''
                        break
                
                # player_name_ja列を探す
                player_name_ja = ''
                for key in row.keys():
                    key_lower = key.lower()
                    if key_lower in ['player_name_ja', 'playername_ja', 'name_ja', '選手名', 'name']:
                        player_name_ja = str(row[key]).strip()
                        if player_name_ja in ['', 'nan', 'None', '-']:
                            player_name_ja = ''
                        break
                
                # team列を探す
                team = ''
                for key in row.keys():
                    key_lower = key.lower()
                    if key_lower in ['team', 'チーム']:
                        team = str(row[key]).strip()
                        if team in ['', 'nan', 'None', '-']:
                            team = ''
                        break
                
                # player_idが空の場合は、player_name_ja + teamの組み合わせで識別
                if not player_id and player_name_ja and team:
                    # 識別子として使用する形式: "player_name_ja::team"
                    identifier = f"{player_name_ja}::{team}"
                elif player_id:
                    identifier = player_id
                else:
                    # どちらもない場合はスキップ
                    continue
                
                identifiers.append((player_id, player_name_ja, team))
    except Exception as e:
        print(f"警告: CSV読み込みエラー ({csv_path}): {e}")
    
    return identifiers


def find_2025_batting_csv_files(search_dirs: List[Path]) -> List[Path]:
    """batting_2025_(PL|CL)_from_master.csv パターンのCSVファイルを検索"""
    csv_files = []
    pattern = re.compile(r'batting_2025_(PL|CL)_from_master\.csv$', re.IGNORECASE)
    
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
    parser = argparse.ArgumentParser(description='2025年の成績CSVからplayer_id（またはplayer_name_ja + team）をユニーク抽出')
    parser.add_argument('--data-dir', type=str, help='成績CSVフォルダのルートディレクトリ')
    parser.add_argument('--output', type=str, default=None, help='出力CSVファイルパス（デフォルト: output/master/all_player_ids_2025.csv）')
    args = parser.parse_args()
    
    # 探索対象ディレクトリ
    search_dirs = [
        project_root / '_data' / 'master_csv',
        project_root / '_data' / 'master_csv_calculated',
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
    
    print("2025年の成績CSVファイルを探索中...")
    csv_files = find_2025_batting_csv_files(search_dirs)
    print(f"   見つかったCSVファイル: {len(csv_files)}件\n")
    
    if not csv_files:
        print("エラー: 2025年の成績CSVファイルが見つかりませんでした")
        return 1
    
    # 各CSVファイルから識別子を抽出
    all_identifiers = {}  # identifier -> (player_id, player_name_ja, team)
    processed_files = 0
    
    for csv_file in csv_files:
        print(f"   処理中: {csv_file.name}...", end=' ', flush=True)
        identifiers = extract_player_identifiers_from_csv(csv_file)
        
        for player_id, player_name_ja, team in identifiers:
            # player_idが空の場合は、player_name_ja + teamの組み合わせで識別
            if not player_id and player_name_ja and team:
                identifier = f"{player_name_ja}::{team}"
            elif player_id:
                identifier = player_id
            else:
                continue
            
            # 既に存在する場合は、player_idを優先（player_idがある方が優先）
            if identifier in all_identifiers:
                existing_player_id, _, _ = all_identifiers[identifier]
                if not existing_player_id and player_id:
                    # 既存がplayer_idなしで、新しい方がplayer_idありの場合は更新
                    all_identifiers[identifier] = (player_id, player_name_ja, team)
            else:
                all_identifiers[identifier] = (player_id, player_name_ja, team)
        
        processed_files += 1
        print(f"OK: {len(identifiers)}件の識別子を抽出")
    
    print(f"\n処理完了: {processed_files}ファイルから {len(all_identifiers)}件のユニーク識別子を抽出")
    
    # 出力ディレクトリを作成
    output_dir = project_root / 'output' / 'master'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 出力パスを決定
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = output_dir / 'all_player_ids_2025.csv'
    
    # CSVに出力
    sorted_identifiers = sorted(all_identifiers.items(), key=lambda x: (len(x[0]), x[0]))
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['identifier', 'player_id', 'player_name_ja', 'team'])
        for identifier, (player_id, player_name_ja, team) in sorted_identifiers:
            writer.writerow([identifier, player_id, player_name_ja, team])
    
    print(f"結果を出力しました: {output_path}")
    
    # サマリーを表示
    player_id_count = sum(1 for _, (pid, _, _) in all_identifiers.items() if pid)
    name_team_count = sum(1 for _, (pid, _, _) in all_identifiers.items() if not pid)
    
    print(f"\nサマリー:")
    print(f"   処理したCSVファイル数: {processed_files}件")
    print(f"   抽出したユニーク識別子数: {len(all_identifiers)}件")
    print(f"   - player_idあり: {player_id_count}件")
    print(f"   - player_name_ja + team（player_idなし）: {name_team_count}件")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
