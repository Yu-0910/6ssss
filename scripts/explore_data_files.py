#!/usr/bin/env python3
"""
explore_data_files.py

npb_battingディレクトリ配下の1936/1937年関連ファイルを広範囲に探索
分割可能性を確認する
"""

import csv
from pathlib import Path
from typing import List, Dict, Any, Set
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


def find_all_csv_files(base_path: Path, pattern: str = "*193[67]*.csv") -> List[Path]:
    """指定パス配下のCSVファイルを再帰的に検索"""
    found_files = []
    if not base_path.exists():
        return found_files
    
    for file_path in base_path.rglob(pattern):
        if file_path.is_file():
            found_files.append(file_path)
    
    return sorted(found_files)


def analyze_file_for_split(csv_path: Path, target_years: List[int]) -> Dict[str, Any]:
    """ファイルを分析して分割可能性を判定"""
    try:
        data = load_csv_with_encoding(csv_path)
    except Exception as e:
        return {
            'path': str(csv_path),
            'readable': False,
            'error': str(e)
        }
    
    if not data:
        return {
            'path': str(csv_path),
            'readable': True,
            'row_count': 0,
            'empty': True
        }
    
    columns = list(data[0].keys())
    
    # year列を探す
    year_column = None
    for col in columns:
        if 'year' in col.lower():
            year_column = col
            break
    
    # 対象年度のデータをフィルタ
    filtered_data = []
    if year_column:
        for row in data:
            try:
                year_val = str(row.get(year_column, '')).strip()
                if any(str(y) in year_val for y in target_years):
                    filtered_data.append(row)
            except:
                pass
    
    if not filtered_data and year_column:
        # フィルタできない場合は全データ
        filtered_data = data
    
    # player_id列を探す
    player_id_column = None
    for col in ['player_id', 'playerId', 'id', '選手ID']:
        if col in columns:
            player_id_column = col
            break
    
    # 重複チェック
    duplicate_check = None
    if player_id_column and year_column:
        key_to_rows = defaultdict(list)
        for row in filtered_data:
            key = (str(row.get(player_id_column, '')).strip(), str(row.get(year_column, '')).strip())
            key_to_rows[key].append(row)
        
        duplicates = {k: rows for k, rows in key_to_rows.items() if len(rows) > 1}
        duplicate_check = {
            'duplicate_count': len(duplicates),
            'total_keys': len(key_to_rows),
            'has_duplicates': len(duplicates) > 0
        }
    
    # season列を探す
    season_column = None
    season_values = set()
    for col in columns:
        if 'season' in col.lower():
            season_column = col
            for row in filtered_data:
                val = str(row.get(col, '')).strip().lower()
                if val:
                    season_values.add(val)
            break
    
    # URL列を探す
    url_columns = []
    for col in columns:
        if 'url' in col.lower() or 'source' in col.lower() or 'page' in col.lower():
            url_columns.append(col)
    
    # URL列から春秋を示すパターンを探す
    url_has_season_info = False
    if url_columns:
        for row in filtered_data[:100]:  # 最初の100行をチェック
            for col in url_columns:
                url = str(row.get(col, '')).strip().lower()
                if any(kw in url for kw in ['spring', 'fall', 'autumn', '春', '秋', '前半', '後半']):
                    url_has_season_info = True
                    break
            if url_has_season_info:
                break
    
    return {
        'path': str(csv_path),
        'readable': True,
        'row_count': len(data),
        'filtered_row_count': len(filtered_data),
        'column_count': len(columns),
        'year_column': year_column,
        'player_id_column': player_id_column,
        'season_column': season_column,
        'season_values': sorted(season_values) if season_values else None,
        'url_columns': url_columns,
        'url_has_season_info': url_has_season_info,
        'duplicate_check': duplicate_check,
        'can_split': (
            (duplicate_check and duplicate_check['has_duplicates']) or
            (season_column and season_values) or
            url_has_season_info
        )
    }


def main():
    # ベースパス
    base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")
    
    if not base_path.exists():
        print(f"[エラー] ベースパスが見つかりません: {base_path}")
        return 1
    
    print("=" * 80)
    print("1936/1937年 データファイル探索スクリプト")
    print("=" * 80)
    print(f"\n探索ベース: {base_path}")
    
    # すべてのCSVファイルを検索
    print("\n[探索中] 1936/1937年関連のCSVファイルを検索中...")
    all_files = find_all_csv_files(base_path, "*193[67]*.csv")
    
    print(f"\n発見されたファイル数: {len(all_files)}")
    
    # 各ファイルを分析
    print("\n" + "=" * 80)
    print("各ファイルの分析結果")
    print("=" * 80)
    
    analysis_results = []
    for file_path in all_files:
        print(f"\n分析中: {file_path.name}")
        result = analyze_file_for_split(file_path, [1936, 1937])
        analysis_results.append(result)
        
        if not result.get('readable'):
            print(f"  [エラー] 読み込めません: {result.get('error', 'Unknown')}")
            continue
        
        print(f"  行数: {result.get('row_count', 0):,}行")
        if result.get('filtered_row_count'):
            print(f"  対象年度フィルタ後: {result.get('filtered_row_count', 0):,}行")
        
        duplicate_check = result.get('duplicate_check')
        if duplicate_check:
            print(f"  重複チェック: {duplicate_check['duplicate_count']}件の重複キー")
            if duplicate_check['has_duplicates']:
                print(f"    -> 分割可能の可能性あり")
        
        if result.get('season_column'):
            print(f"  season列: {result['season_column']} (値: {result.get('season_values', [])})")
            print(f"    -> 分割可能")
        
        if result.get('url_has_season_info'):
            print(f"  URL列: 春秋情報が含まれている可能性あり")
            print(f"    -> 分割可能")
        
        if result.get('can_split'):
            print(f"  [結論] 分割可能")
        else:
            print(f"  [結論] 分割困難（情報不足）")
    
    # 分割可能なファイルをリストアップ
    print("\n" + "=" * 80)
    print("分割可能なファイル")
    print("=" * 80)
    
    splittable_files = [r for r in analysis_results if r.get('can_split')]
    if splittable_files:
        for result in splittable_files:
            print(f"\n{Path(result['path']).name}")
            print(f"  パス: {result['path']}")
            reasons = []
            if result.get('duplicate_check', {}).get('has_duplicates'):
                reasons.append("重複あり")
            if result.get('season_column'):
                reasons.append(f"season列あり ({result['season_column']})")
            if result.get('url_has_season_info'):
                reasons.append("URL列に春秋情報あり")
            print(f"  理由: {', '.join(reasons)}")
    else:
        print("\n分割可能なファイルが見つかりませんでした。")
    
    # レポートを保存
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_dir = project_root / 'output' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = output_dir / 'explore_data_files_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 1936/1937年 データファイル探索レポート\n\n")
        f.write(f"探索ベース: {base_path}\n\n")
        f.write(f"発見されたファイル数: {len(all_files)}\n\n")
        
        f.write("## 全ファイル一覧\n\n")
        for file_path in all_files:
            f.write(f"- {file_path}\n")
        
        f.write("\n## 分析結果\n\n")
        for result in analysis_results:
            f.write(f"### {Path(result['path']).name}\n\n")
            f.write(f"- **パス**: `{result['path']}`\n")
            f.write(f"- **読み込み可能**: {'はい' if result.get('readable') else 'いいえ'}\n")
            if not result.get('readable'):
                f.write(f"- **エラー**: {result.get('error', 'Unknown')}\n\n")
                continue
            
            f.write(f"- **行数**: {result.get('row_count', 0):,}行\n")
            if result.get('filtered_row_count'):
                f.write(f"- **対象年度フィルタ後行数**: {result.get('filtered_row_count', 0):,}行\n")
            f.write(f"- **列数**: {result.get('column_count', 0)}列\n")
            
            if result.get('season_column'):
                f.write(f"- **season列**: {result['season_column']}\n")
                if result.get('season_values'):
                    f.write(f"  - 値: {', '.join(result['season_values'])}\n")
            
            if result.get('url_columns'):
                f.write(f"- **URL列**: {', '.join(result['url_columns'])}\n")
                f.write(f"  - 春秋情報あり: {'はい' if result.get('url_has_season_info') else 'いいえ'}\n")
            
            duplicate_check = result.get('duplicate_check')
            if duplicate_check:
                f.write(f"- **重複チェック**:\n")
                f.write(f"  - 重複キー数: {duplicate_check['duplicate_count']}\n")
                f.write(f"  - 総キー数: {duplicate_check['total_keys']}\n")
            
            f.write(f"- **分割可能性**: {'可能' if result.get('can_split') else '困難'}\n")
            f.write("\n")
        
        f.write("## 分割可能なファイル\n\n")
        if splittable_files:
            for result in splittable_files:
                f.write(f"- `{result['path']}`\n")
        else:
            f.write("分割可能なファイルは見つかりませんでした。\n")
    
    print(f"\n[完了] レポートを保存: {report_path}")
    
    return 0


if __name__ == '__main__':
    exit(main())





















