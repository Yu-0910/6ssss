#!/usr/bin/env python3
"""
STEP 5: 成績CSVへ反映→ランキングJSON再生成
"""

import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent


def to_initial_lastname(full_name: str, is_japanese: bool = False) -> str:
    """
    完全な名前を「イニシャル.苗字」形式に変換
    
    外国人選手の場合（is_japanese=False）:
        "Roman Mejias" → "R.Mejias" （名前のイニシャル.苗字）
    
    日本人選手の場合（is_japanese=True）:
        "Sato Shigeo" → "S.Sato" （名前のイニシャル.苗字）
        ただし、入力は「苗字 名前」の順序であることを想定
    """
    if not full_name:
        return ''
    
    # 空白で分割
    parts = full_name.strip().split()
    
    if len(parts) == 0:
        return ''
    
    # 既にイニシャル.苗字形式（例: "R.Mejias", "S.Sato"）の場合はそのまま返す
    if len(parts) == 1 and '.' in parts[0]:
        return parts[0]
    
    if len(parts) == 1:
        # 1単語のみの場合（苗字のみ、または名前のみ）
        name = parts[0].strip()
        if len(name) > 0:
            initial = name[0].upper()
            return f"{initial}.{name}"
        return ''
    
    # 複数の単語がある場合
    if is_japanese:
        # 日本人選手の場合: 「苗字 名前」→「名前のイニシャル.苗字」
        # 例: "Sato Shigeo" → "S.Sato"
        last_name = parts[0].strip()  # 最初の部分が苗字
        first_name = parts[-1].strip()  # 最後の部分が名前
        
        if not first_name or not last_name:
            return full_name
        
        # 名前の最初の文字をイニシャルとして取得
        initial = first_name[0].upper()
        
        # 苗字をTitle Caseに変換（先頭大文字、他小文字）
        last_name_title = last_name[0].upper() + last_name[1:].lower() if len(last_name) > 1 else last_name.upper()
        
        return f"{initial}.{last_name_title}"
    else:
        # 外国人選手の場合: 「名前 苗字」→「名前のイニシャル.苗字」
        # 例: "Roman Mejias" → "R.Mejias"
        first_name = parts[0].strip()  # 最初の部分が名前
        last_name = parts[-1].strip()  # 最後の部分が苗字
        
        if not first_name or not last_name:
            return full_name
        
        # 名前の最初の文字をイニシャルとして取得
        initial = first_name[0].upper()
        
        # 苗字をTitle Caseに変換（先頭大文字、他小文字）
        last_name_title = last_name[0].upper() + last_name[1:].lower() if len(last_name) > 1 else last_name.upper()
        
        return f"{initial}.{last_name_title}"


def is_full_name_format(roman_name: str) -> bool:
    """フルネーム形式（例: "Nishikawa Manaya", "Matsubara Seiya"）かどうかを判定"""
    if not roman_name or not roman_name.strip():
        return False
    
    # 既にイニシャル.苗字形式（例: "R.Mejias", "S.Sato"）の場合はFalse
    if '.' in roman_name and re.match(r'^[A-Z]\.[A-Z][a-z]+$', roman_name.strip()):
        return False
    
    # 空白が含まれていて、2単語以上ある場合はフルネーム形式の可能性が高い
    parts = roman_name.strip().split()
    return len(parts) >= 2 and not any('.' in part for part in parts)


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


def load_roman_dict(roman_dict_path: Path) -> Dict[str, Dict]:
    """最終辞書CSVを読み込む"""
    roman_dict = {}
    
    if not roman_dict_path.exists():
        print(f"❌ 辞書ファイルが見つかりません: {roman_dict_path}")
        return roman_dict
    
    with open(roman_dict_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            player_id = row.get('player_id', '').strip()
            if player_id:
                roman_dict[player_id] = {
                    'romanName': row.get('romanName', '').strip(),
                    'source': row.get('source', '').strip(),
                }
    
    return roman_dict


def find_batting_csv_files(search_dirs: List[Path]) -> List[Path]:
    """batting_YYYY_(PL|CL)_from_master.csv パターンのCSVファイルを検索"""
    csv_files = []
    pattern = re.compile(r'batting_\d{4}_(PL|CL)_from_master\.csv$', re.IGNORECASE)
    
    for search_dir in search_dirs:
        if not search_dir.exists() or not search_dir.is_dir():
            continue
        
        for csv_file in search_dir.rglob('*.csv'):
            if 'node_modules' in str(csv_file) or '.next' in str(csv_file):
                continue
            
            if pattern.search(csv_file.name):
                csv_files.append(csv_file)
    
    return sorted(csv_files)


def apply_roman_to_csv(csv_path: Path, roman_dict: Dict[str, Dict], dry_run: bool = False) -> Dict:
    """CSVファイルにromanNameを適用"""
    encoding = detect_encoding(csv_path)
    
    # 読み込み
    rows = []
    headers = None
    
    try:
        with open(csv_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            if not headers:
                return {'updated': 0, 'skipped': 0, 'error': 'No headers'}
            
            for row in reader:
                rows.append(row)
    except Exception as e:
        return {'updated': 0, 'skipped': 0, 'error': str(e)}
    
    # player_id列を探す
    player_id_key = None
    for key in headers:
        if key.lower() in ['player_id', 'playerid', 'id']:
            player_id_key = key
            break
    
    if not player_id_key:
        return {'updated': 0, 'skipped': 0, 'error': 'player_id column not found'}
    
    # romanName列を追加（存在しない場合）
    roman_name_key = None
    for key in ['player_name_en', 'romanName', 'roman_name', 'name_en']:
        if key in headers:
            roman_name_key = key
            break
    
    if not roman_name_key:
        # 新しい列を追加
        roman_name_key = 'player_name_en'
        headers = list(headers) + [roman_name_key]
    
    # 各行を処理
    updated_count = 0
    skipped_count = 0
    
    for row in rows:
        player_id = str(row.get(player_id_key, '')).strip()
        if not player_id:
            skipped_count += 1
            continue
        
        # 既存の値を取得
        current_roman = row.get(roman_name_key, '').strip()
        
        # 既にイニシャル.苗字形式の場合はスキップ
        if current_roman and current_roman not in ['', 'nan', 'None', '-']:
            # フルネーム形式（例: "Nishikawa Manaya"）の場合は辞書の値で上書き
            if is_full_name_format(current_roman):
                # フルネーム形式を検出したが、辞書に値がある場合は辞書の値を使用
                if player_id in roman_dict:
                    roman_name = roman_dict[player_id]['romanName']
                    if roman_name:
                        row[roman_name_key] = roman_name
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    skipped_count += 1
            else:
                # 既にイニシャル.苗字形式の場合はスキップ
                skipped_count += 1
            continue
        
        # 辞書から取得
        if player_id in roman_dict:
            roman_name = roman_dict[player_id]['romanName']
            if roman_name:
                row[roman_name_key] = roman_name
                updated_count += 1
            else:
                skipped_count += 1
        else:
            skipped_count += 1
    
    # 書き込み（dry-runでない場合）
    if not dry_run:
        try:
            with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            return {'updated': updated_count, 'skipped': skipped_count, 'error': str(e)}
    
    return {'updated': updated_count, 'skipped': skipped_count, 'error': None}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='成績CSVへromanNameを反映')
    parser.add_argument('--roman-dict', type=str, default=None, help='最終辞書CSV（デフォルト: output/master/player_id_to_roman_full.csv）')
    parser.add_argument('--data-dir', type=str, default=None, help='成績CSVフォルダ（デフォルト: _data/master_csv_calculated）')
    parser.add_argument('--dry-run', action='store_true', help='書き込みなしで確認のみ')
    args = parser.parse_args()
    
    # 辞書パスを決定
    if args.roman_dict:
        roman_dict_path = Path(args.roman_dict)
    else:
        roman_dict_path = project_root / 'output' / 'master' / 'player_id_to_roman_full.csv'
    
    # 辞書を読み込む
    print(f"📖 辞書を読み込み中: {roman_dict_path}")
    roman_dict = load_roman_dict(roman_dict_path)
    print(f"✅ {len(roman_dict)}件のplayer_idを読み込みました")
    
    if not roman_dict:
        print("❌ 辞書が空です")
        return 1
    
    # 探索対象ディレクトリ
    search_dirs = []
    if args.data_dir:
        search_dirs.append(Path(args.data_dir))
    else:
        search_dirs.append(project_root / '_data' / 'master_csv_calculated')
        search_dirs.append(project_root / '_data' / 'master_csv')
    
    # CSVファイルを検索
    print("\n🔍 成績CSVファイルを探索中...")
    csv_files = find_batting_csv_files(search_dirs)
    print(f"   見つかったCSVファイル: {len(csv_files)}件\n")
    
    if not csv_files:
        print("❌ 成績CSVファイルが見つかりませんでした")
        return 1
    
    # 各CSVファイルを処理
    total_updated = 0
    total_skipped = 0
    
    for csv_file in csv_files:
        print(f"   処理中: {csv_file.name}...", end=' ', flush=True)
        result = apply_roman_to_csv(csv_file, roman_dict, args.dry_run)
        
        if result.get('error'):
            print(f"❌ エラー: {result['error']}")
        else:
            updated = result['updated']
            skipped = result['skipped']
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











