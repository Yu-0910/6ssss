#!/usr/bin/env python3
"""
2025年のランキングページで英字名前が未完成の選手について、
2024年以前のデータから英字名前をコピーして適用するスクリプト
"""

import csv
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

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
                f.read(1024)
            return encoding
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return 'utf-8'


def normalize_player_name(name: str) -> str:
    """選手名を正規化（全角スペースを半角に、連続スペースを1つに）"""
    if not name:
        return ''
    normalized = name.replace('\u3000', ' ').replace('　', ' ')
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()


def load_roman_names_from_previous_years(
    data_dir: Path,
    years: range = range(1950, 2025)
) -> Dict[str, str]:
    """
    2024年以前のCSVファイルから英字名前を収集
    
    Returns:
        Dict[identifier, roman_name]
        identifierは player_id または "player_name_ja::team" の形式
    """
    roman_name_map: Dict[str, str] = {}
    
    # 対象ディレクトリ
    search_dirs = [
        data_dir / 'master_csv_calculated',
        data_dir / 'master_csv',
        data_dir / 'master_csv__import_1950_2024',
    ]
    
    # 対象年度のCSVファイルを検索
    pattern = re.compile(r'batting_(\d{4})_(PL|CL)_from_master\.csv$', re.IGNORECASE)
    
    csv_files = []
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for csv_file in search_dir.rglob('*.csv'):
            if 'node_modules' in str(csv_file) or '.next' in str(csv_file):
                continue
            match = pattern.search(csv_file.name)
            if match:
                year = int(match.group(1))
                if year in years:
                    csv_files.append(csv_file)
    
    print(f"📁 {len(csv_files)}件のCSVファイルを検索しました")
    
    # 各CSVファイルから英字名前を収集
    processed_files = 0
    total_roman_names = 0
    
    for csv_file in csv_files:
        encoding = detect_encoding(csv_file)
        try:
            with open(csv_file, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # player_idを取得
                    player_id = ''
                    for key in row.keys():
                        key_lower = key.lower()
                        if key_lower in ['player_id', 'playerid', 'id']:
                            player_id = str(row[key]).strip()
                            if player_id in ['', 'nan', 'None', '-']:
                                player_id = ''
                            break
                    
                    # player_name_jaを取得
                    player_name_ja = ''
                    for key in row.keys():
                        key_lower = key.lower()
                        if key_lower in ['player_name_ja', 'playername_ja', 'name_ja', '選手名', 'name']:
                            player_name_ja = str(row[key]).strip()
                            if player_name_ja in ['', 'nan', 'None', '-']:
                                player_name_ja = ''
                            break
                    
                    # teamを取得
                    team = ''
                    for key in row.keys():
                        key_lower = key.lower()
                        if key_lower in ['team', 'チーム']:
                            team = str(row[key]).strip()
                            if team in ['', 'nan', 'None', '-']:
                                team = ''
                            break
                    
                    # player_name_enを取得
                    player_name_en = ''
                    for key in row.keys():
                        key_lower = key.lower()
                        if key_lower in ['player_name_en', 'playername_en', 'name_en', 'romanname', 'roman_name', 'english_name']:
                            player_name_en = str(row[key]).strip()
                            if player_name_en in ['', 'nan', 'None', '-']:
                                player_name_en = ''
                            break
                    
                    # 英字名前が存在する場合のみ処理
                    if not player_name_en:
                        continue
                    
                    # identifierを複数作成（player_idとplayer_name_ja + teamの両方）
                    identifiers = []
                    
                    # player_idがある場合は、player_idをidentifierとして追加
                    if player_id:
                        identifiers.append(player_id)
                    
                    # player_name_ja + teamの組み合わせもidentifierとして追加
                    if player_name_ja and team:
                        normalized_name = normalize_player_name(player_name_ja)
                        normalized_team = team.strip()
                        name_team_identifier = f"{normalized_name}::{normalized_team}"
                        identifiers.append(name_team_identifier)
                    
                    if not identifiers:
                        continue
                    
                    # 各identifierに対して英字名前を登録
                    for identifier in identifiers:
                        # 既に存在する場合は、より長い（完全な）英字名前を優先
                        # ただし、既に「イニシャル.苗字」形式の場合は、フルネーム形式を優先
                        if identifier in roman_name_map:
                            existing = roman_name_map[identifier]
                            # 既存が「イニシャル.苗字」形式で、新しい方がフルネーム形式の場合は更新
                            if '.' in existing and len(existing.split('.')) == 2 and len(existing.split('.')[0]) == 1:
                                # 既存が「M.Kozuru」形式の場合
                                if ' ' in player_name_en and len(player_name_en.split(' ')) >= 2:
                                    # 新しい方がフルネーム形式の場合は更新
                                    roman_name_map[identifier] = player_name_en
                            elif len(player_name_en) > len(existing):
                                roman_name_map[identifier] = player_name_en
                        else:
                            roman_name_map[identifier] = player_name_en
                            total_roman_names += 1
            
            processed_files += 1
            if processed_files % 50 == 0:
                print(f"   処理中: {processed_files}/{len(csv_files)}ファイル...")
        except Exception as e:
            print(f"⚠️  エラー ({csv_file.name}): {e}")
            continue
    
    print(f"✅ {processed_files}ファイルから {total_roman_names}件の英字名前を収集しました")
    print(f"   ユニークidentifier数: {len(roman_name_map)}件")
    
    return roman_name_map


def update_2025_csv_with_roman_names(
    csv_path: Path,
    roman_name_map: Dict[str, str],
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    2025年のCSVファイルを更新して英字名前を適用
    
    Returns:
        (updated_count, skipped_count)
    """
    encoding = detect_encoding(csv_path)
    
    # 読み込み
    rows = []
    headers = None
    
    try:
        with open(csv_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames)
            if not headers:
                return 0, 0
            
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"❌ CSV読み込みエラー ({csv_path}): {e}")
        return 0, 0
    
    # player_name_en列を探す（存在しない場合は追加）
    player_name_en_key = None
    for key in ['player_name_en', 'playername_en', 'name_en', 'romanname', 'roman_name']:
        if key in headers:
            player_name_en_key = key
            break
    
    if not player_name_en_key:
        player_name_en_key = 'player_name_en'
        headers.append(player_name_en_key)
    
    # 各行を処理
    updated_count = 0
    skipped_count = 0
    
    for row in rows:
        # player_idを取得
        player_id = ''
        for key in row.keys():
            key_lower = key.lower()
            if key_lower in ['player_id', 'playerid', 'id']:
                player_id = str(row[key]).strip()
                if player_id in ['', 'nan', 'None', '-']:
                    player_id = ''
                break
        
        # player_name_jaを取得
        player_name_ja = ''
        for key in row.keys():
            key_lower = key.lower()
            if key_lower in ['player_name_ja', 'playername_ja', 'name_ja', '選手名', 'name']:
                player_name_ja = str(row[key]).strip()
                if player_name_ja in ['', 'nan', 'None', '-']:
                    player_name_ja = ''
                break
        
        # teamを取得
        team = ''
        for key in row.keys():
            key_lower = key.lower()
            if key_lower in ['team', 'チーム']:
                team = str(row[key]).strip()
                if team in ['', 'nan', 'None', '-']:
                    team = ''
                break
        
        # 現在の英字名前を取得（確認用のみ）
        current_roman = row.get(player_name_en_key, '').strip()
        
        # identifierを作成
        identifier = None
        if player_id:
            identifier = player_id
        elif player_name_ja and team:
            normalized_name = normalize_player_name(player_name_ja)
            identifier = f"{normalized_name}::{team}"
        
        if not identifier:
            skipped_count += 1
            continue
        
        # 英字名前を検索
        roman_name = roman_name_map.get(identifier)
        if not roman_name:
            # デバッグ出力（最初の5件のみ）
            if skipped_count < 5:
                print(f"      [スキップ] {player_name_ja} ({team}): identifier='{identifier}' が見つかりません")
            skipped_count += 1
            continue
        
        # 既に英字名前がある場合でも、2024年以前のデータから取得した英字名前で上書き
        # （ただし、既に同じ値の場合はスキップ）
        if current_roman == roman_name:
            skipped_count += 1
            continue
        
        # 英字名前を設定
        row[player_name_en_key] = roman_name
        updated_count += 1
        
        # デバッグ出力（最初の10件のみ）
        if updated_count <= 10:
            print(f"      [{updated_count}] {player_name_ja} ({team}): '{current_roman}' → '{roman_name}' (identifier: {identifier})")
    
    # 書き込み（dry-runでない場合）
    if not dry_run:
        try:
            with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            print(f"❌ CSV書き込みエラー ({csv_path}): {e}")
            return updated_count, skipped_count
    
    return updated_count, skipped_count


def main():
    import argparse
    parser = argparse.ArgumentParser(description='2024年以前のデータから英字名前をコピーして2025年のデータに適用')
    parser.add_argument('--data-dir', type=str, default=None, help='データディレクトリ（デフォルト: _data）')
    parser.add_argument('--dry-run', action='store_true', help='書き込みなしで確認のみ')
    parser.add_argument('--years', type=str, default='1950-2024', help='対象年度範囲（デフォルト: 1950-2024）')
    args = parser.parse_args()
    
    # データディレクトリを決定
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = project_root / '_data'
    
    if not data_dir.exists():
        print(f"❌ データディレクトリが見つかりません: {data_dir}")
        return 1
    
    # 年度範囲を解析
    if '-' in args.years:
        start_year, end_year = map(int, args.years.split('-'))
        years = range(start_year, end_year + 1)
    else:
        years = range(1950, 2025)
    
    print(f"📖 2024年以前のデータから英字名前を収集中...")
    print(f"   対象年度: {years.start}年 ～ {years.stop - 1}年")
    
    # 2024年以前のデータから英字名前を収集
    roman_name_map = load_roman_names_from_previous_years(data_dir, years)
    
    if not roman_name_map:
        print("❌ 英字名前が見つかりませんでした")
        return 1
    
    # 2025年のCSVファイルを検索
    print(f"\n📝 2025年のCSVファイルを検索中...")
    pattern = re.compile(r'batting_2025_(PL|CL)_from_master\.csv$', re.IGNORECASE)
    
    csv_files = []
    search_dirs = [
        data_dir / 'master_csv_calculated',
        data_dir / 'master_csv',
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for csv_file in search_dir.rglob('*.csv'):
            if pattern.search(csv_file.name):
                csv_files.append(csv_file)
    
    csv_files = sorted(csv_files)
    print(f"   見つかったCSVファイル: {len(csv_files)}件")
    
    if not csv_files:
        print("❌ 2025年のCSVファイルが見つかりませんでした")
        return 1
    
    # 各CSVファイルを更新
    total_updated = 0
    total_skipped = 0
    
    for csv_file in csv_files:
        print(f"\n   処理中: {csv_file.name}...", end=' ', flush=True)
        updated, skipped = update_2025_csv_with_roman_names(csv_file, roman_name_map, args.dry_run)
        total_updated += updated
        total_skipped += skipped
        
        if args.dry_run:
            print(f"✅ [DRY-RUN] 更新予定: {updated}件, スキップ: {skipped}件")
        else:
            print(f"✅ 更新: {updated}件, スキップ: {skipped}件")
    
    print(f"\n📊 サマリー:")
    print(f"   処理したCSVファイル数: {len(csv_files)}件")
    print(f"   総更新数: {total_updated}件")
    print(f"   総スキップ数: {total_skipped}件")
    
    if args.dry_run:
        print("\n⚠️  DRY-RUNモード: 実際のファイルは更新されていません")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
