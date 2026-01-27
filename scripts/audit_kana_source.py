#!/usr/bin/env python3
"""
STEP 1: プロジェクト内のCSVファイルから「読み（かな）」列を探索・選定するスクリプト
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent

# 読み（かな）列の候補名
KANA_COLUMN_CANDIDATES = [
    'kana', 'yomi', 'furigana', 'name_kana', 'player_name_kana', 'katakana', 'reading',
    'ふりがな', 'フリガナ', 'よみ', '読み', '読み仮名', 'カナ', 'かな', 'name_kana', 'player_kana'
]

# player_id列の候補名
PLAYER_ID_CANDIDATES = [
    'player_id', 'playerId', 'playerid', 'id', 'ID', '選手ID', 'playerID'
]

# 選手名列の候補名
PLAYER_NAME_CANDIDATES = [
    'player_name_ja', 'player_name', 'name', 'Name', 'NAME', '選手名', 'name_ja', 'player'
]


def detect_encoding(file_path: Path) -> Optional[str]:
    """ファイルの文字コードを検出"""
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)  # 先頭1KBを読んでみる
            return encoding
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return None


def analyze_csv_file(csv_path: Path) -> Optional[Dict]:
    """CSVファイルを分析して、読み（かな）列の有無を確認"""
    encoding = detect_encoding(csv_path)
    if not encoding:
        return None
    
    try:
        with open(csv_path, 'r', encoding=encoding) as f:
            # 先頭2行を読んでヘッダーとサンプルデータを確認
            first_line = f.readline()
            second_line = f.readline()
            
            if not first_line:
                return None
            
            # ヘッダーを解析
            # カンマ区切りを試す
            headers = [h.strip().lstrip('\ufeff') for h in first_line.rstrip('\r\n').split(',')]
            if len(headers) == 1:
                # タブ区切りを試す
                headers = [h.strip().lstrip('\ufeff') for h in first_line.rstrip('\r\n').split('\t')]
            
            # 空文字を除去
            headers = [h for h in headers if h]
            
            if not headers:
                return None
            
            # 読み（かな）列を探す
            kana_column = None
            for header in headers:
                header_lower = header.lower()
                header_normalized = header.replace(' ', '').replace('　', '').replace('_', '').replace('-', '')
                
                for candidate in KANA_COLUMN_CANDIDATES:
                    if candidate.lower() in header_lower or candidate in header_normalized:
                        kana_column = header
                        break
                
                if kana_column:
                    break
            
            # player_id列を探す
            has_player_id = False
            player_id_column = None
            for header in headers:
                header_lower = header.lower()
                for candidate in PLAYER_ID_CANDIDATES:
                    if candidate.lower() == header_lower:
                        has_player_id = True
                        player_id_column = header
                        break
                if has_player_id:
                    break
            
            # 選手名列を探す
            player_name_column = None
            for header in headers:
                header_lower = header.lower()
                for candidate in PLAYER_NAME_CANDIDATES:
                    if candidate.lower() in header_lower:
                        player_name_column = header
                        break
                if player_name_column:
                    break
            
            # データ行を読んで網羅率を計算
            f.seek(0)
            reader = csv.DictReader(f)
            
            total_rows = 0
            kana_filled_rows = 0
            player_id_filled_rows = 0
            
            for row in reader:
                total_rows += 1
                
                if kana_column and kana_column in row:
                    kana_value = str(row[kana_column]).strip()
                    if kana_value and kana_value not in ['', 'nan', 'None', '-']:
                        # ひらがな・カタカナが含まれているか確認
                        if re.search(r'[あ-んア-ン]', kana_value):
                            kana_filled_rows += 1
                
                if has_player_id and player_id_column and player_id_column in row:
                    player_id_value = str(row[player_id_column]).strip()
                    if player_id_value and player_id_value not in ['', 'nan', 'None', '-']:
                        player_id_filled_rows += 1
            
            coverage_rate = (kana_filled_rows / total_rows * 100) if total_rows > 0 else 0.0
            player_id_coverage = (player_id_filled_rows / total_rows * 100) if total_rows > 0 else 0.0
            
            notes = []
            if not kana_column:
                notes.append("読み（かな）列が見つかりません")
            if not has_player_id:
                notes.append("player_id列が見つかりません")
            if not player_name_column:
                notes.append("選手名列が見つかりません")
            
            return {
                'file_path': str(csv_path.relative_to(project_root)),
                'kana_column': kana_column or '',
                'has_player_id': has_player_id,
                'player_id_column': player_id_column or '',
                'player_name_column': player_name_column or '',
                'total_rows': total_rows,
                'kana_filled_rows': kana_filled_rows,
                'coverage_rate': round(coverage_rate, 1),
                'player_id_coverage': round(player_id_coverage, 1),
                'notes': '; '.join(notes) if notes else 'OK'
            }
    
    except Exception as e:
        return {
            'file_path': str(csv_path.relative_to(project_root)),
            'kana_column': '',
            'has_player_id': False,
            'player_id_column': '',
            'player_name_column': '',
            'total_rows': 0,
            'kana_filled_rows': 0,
            'coverage_rate': 0.0,
            'player_id_coverage': 0.0,
            'notes': f'エラー: {str(e)}'
        }


def find_csv_files(search_dirs: List[Path]) -> List[Path]:
    """指定ディレクトリ配下のCSVファイルを再帰的に検索"""
    csv_files = []
    for search_dir in search_dirs:
        if search_dir.exists() and search_dir.is_dir():
            for csv_file in search_dir.rglob('*.csv'):
                # node_modulesや.nextは除外
                if 'node_modules' not in str(csv_file) and '.next' not in str(csv_file):
                    csv_files.append(csv_file)
    return csv_files


def main():
    import argparse
    parser = argparse.ArgumentParser(description='プロジェクト内のCSVから「読み（かな）」列を探索')
    parser.add_argument('--search-dir', type=str, action='append', help='追加で探索するディレクトリ（複数指定可、絶対パスまたは相対パス）')
    parser.add_argument('--data-dir', type=str, help='成績CSVフォルダ（1936〜全期間）のパス（例: C:/data/baseball_csv/）')
    args = parser.parse_args()
    
    # 探索対象ディレクトリ
    search_dirs = [
        project_root / '_data',
        project_root / 'output',
        project_root,
    ]
    
    # 追加の探索ディレクトリ
    if args.search_dir:
        for dir_path in args.search_dir:
            search_dirs.append(Path(dir_path))
    
    # 成績CSVフォルダ（1936〜全期間）
    if args.data_dir:
        data_dir = Path(args.data_dir)
        if data_dir.exists():
            search_dirs.append(data_dir)
            print(f"📁 追加探索ディレクトリ: {data_dir}")
        else:
            print(f"⚠️  指定されたディレクトリが存在しません: {data_dir}")
    
    print("🔍 CSVファイルを探索中...")
    csv_files = find_csv_files(search_dirs)
    print(f"   見つかったCSVファイル: {len(csv_files)}件\n")
    
    if not csv_files:
        print("❌ CSVファイルが見つかりませんでした")
        return 1
    
    # 各CSVファイルを分析
    results = []
    for csv_file in csv_files:
        print(f"   分析中: {csv_file.name}...", end=' ', flush=True)
        result = analyze_csv_file(csv_file)
        if result:
            results.append(result)
            if result['kana_column']:
                print(f"✅ 読み列あり: {result['kana_column']} (網羅率: {result['coverage_rate']}%)")
            else:
                print("❌ 読み列なし")
        else:
            print("⚠️  解析失敗")
    
    # 出力ディレクトリを作成
    output_dir = project_root / 'output' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'kana_source_audit.csv'
    
    # CSVに出力
    fieldnames = ['file_path', 'kana_column', 'has_player_id', 'player_id_column', 'player_name_column', 
                  'total_rows', 'kana_filled_rows', 'coverage_rate', 'player_id_coverage', 'notes']
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✅ 結果を出力しました: {output_path}")
    
    # サマリーを表示
    print("\n📊 サマリー:")
    
    # 読み列があるファイル
    files_with_kana = [r for r in results if r['kana_column']]
    print(f"   読み（かな）列があるファイル: {len(files_with_kana)}件")
    
    if files_with_kana:
        # player_idがあるファイル
        files_with_kana_and_id = [r for r in files_with_kana if r['has_player_id']]
        print(f"   読み列 + player_id があるファイル: {len(files_with_kana_and_id)}件")
        
        # 網羅率が高い順にソート
        files_with_kana.sort(key=lambda x: x['coverage_rate'], reverse=True)
        
        print(f"\n📈 読み列があるファイル（網羅率順）:")
        for i, result in enumerate(files_with_kana[:10], 1):
            print(f"   {i}. {result['file_path']}")
            print(f"      列名: {result['kana_column']}")
            print(f"      網羅率: {result['coverage_rate']}% ({result['kana_filled_rows']}/{result['total_rows']})")
            print(f"      player_id: {'あり' if result['has_player_id'] else 'なし'}")
            if result['notes']:
                print(f"      備考: {result['notes']}")
            print()
        
        # 最適なソースを選定
        best_source = None
        if files_with_kana_and_id:
            # player_idがある中で網羅率が最も高いもの
            best_source = max(files_with_kana_and_id, key=lambda x: x['coverage_rate'])
        elif files_with_kana:
            # player_idがなくても、網羅率が最も高いもの
            best_source = files_with_kana[0]
        
        if best_source:
            print(f"🎯 推奨ソース:")
            print(f"   ファイル: {best_source['file_path']}")
            print(f"   読み列: {best_source['kana_column']}")
            print(f"   網羅率: {best_source['coverage_rate']}%")
            print(f"   player_id: {'あり' if best_source['has_player_id'] else 'なし（選手名で突合が必要）'}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

